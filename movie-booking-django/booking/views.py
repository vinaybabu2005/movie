import base64
import binascii
import io
import json
import re
import uuid
from datetime import date, datetime, timedelta
from PIL import Image, UnidentifiedImageError
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError, RequestDataTooBig
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import IntegrityError, OperationalError, transaction
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie
from .models import Movie, TicketClass, Booking, SeatReservation

@ensure_csrf_cookie
def index(request):
    return render(request, 'index.html')

def csrf_failure(request, reason=''):
    return JsonResponse({'error':'Session security check failed. Refresh the page and try again.'},status=403)

def public_user(user):
    if not user.is_authenticated: return None
    return {'id':user.pk,'name':user.first_name or user.username,'phone':user.username,'role':'admin' if user.is_superuser else 'user'}

def movie_data(m):
    return {'id':m.pk,'title':m.title,'lang':m.lang,'genre':m.genre,'poster':m.poster,'times':m.times}

def booking_data(b):
    return {'ref':b.ref,'userId':b.user_id,'name':b.user.first_name or b.user.username,'phone':b.user.username,'movieId':b.movie_id,'movie':b.movie_title,'date':b.date.isoformat(),'time':b.time,'seats':b.seats,'amount':b.amount,'createdAt':b.created_at.isoformat()}

def require_method(request, method):
    if request.method != method: raise ApiError('Method not allowed',405)

class ApiError(Exception):
    def __init__(self,message,status=400): self.message,self.status=message,status

def text(body,key,max_length=250):
    value=body.get(key,'')
    if not isinstance(value,str) or len(value)>max_length: raise ApiError('Invalid '+key)
    return value.strip()

def show_details(data):
    try:
        mv=Movie.objects.get(pk=int(data.get('movieId')),active=True)
        day=date.fromisoformat(data.get('date',''))
    except (TypeError,ValueError,Movie.DoesNotExist): raise ApiError('Choose a valid movie and date')
    show=data.get('time')
    if show not in mv.times: raise ApiError('Choose a valid show time')
    if day < timezone.localdate(): raise ApiError('Choose today or a later date')
    return mv,day,show

def clean_movie(body):
    title=text(body,'title',80)
    raw=body.get('times',[])
    if isinstance(raw,str): raw=raw.split(',')
    if not isinstance(raw,list): raise ApiError('Enter show times separated by commas')
    times=[]
    for t in raw:
        if not isinstance(t,str): raise ApiError('Invalid show time')
        try: formatted=datetime.strptime(t.strip(),'%I:%M %p').strftime('%I:%M %p').lstrip('0')
        except ValueError: raise ApiError('Use show times like 10:00 AM, 1:30 PM')
        if formatted not in times: times.append(formatted)
    if not title or not 1<=len(times)<=10: raise ApiError('Title and 1 to 10 show times are required')
    poster=text(body,'poster')
    if poster and not re.fullmatch(r'/(?:static/images|media/posters)/[a-zA-Z0-9_-]+\.(?:png|jpg|jpeg|webp)',poster): raise ApiError('Choose an uploaded poster image')
    return {'title':title,'lang':text(body,'lang',30) or 'Telugu','genre':text(body,'genre',40),'poster':poster,'times':times}

def api(request,endpoint):
    try:
        return JsonResponse(dispatch(request,endpoint))
    except ApiError as e: return JsonResponse({'error':e.message},status=e.status)
    except ValidationError as e: return JsonResponse({'error':' '.join(e.messages)},status=400)
    except (json.JSONDecodeError,UnicodeDecodeError,RequestDataTooBig): return JsonResponse({'error':'Invalid request or image too large'},status=400)
    except IntegrityError: return JsonResponse({'error':'That account or seat is already taken. Refresh and try again.'},status=409)
    except OperationalError: return JsonResponse({'error':'Database unavailable or busy. Check migrations, then try again.'},status=503)

def dispatch(request,endpoint):
    body={}
    if request.method in ('POST','PUT','DELETE'):
        body=json.loads(request.body or b'{}')
        if not isinstance(body,dict): raise ApiError('Invalid request')
    user=request.user
    if endpoint=='config':
        require_method(request,'GET')
        return {'me':public_user(user),'movies':[movie_data(m) for m in Movie.objects.filter(active=True).order_by('id')], 'classes':list(TicketClass.objects.order_by('id').values('name','price','cols','rows'))}
    if endpoint=='register':
        require_method(request,'POST')
        name,phone,password=text(body,'name',60),text(body,'phone',10),body.get('password','')
        if not name or not re.fullmatch(r'\d{10}',phone): raise ApiError('Enter your name and a 10-digit phone number')
        if not isinstance(password,str) or len(password)>128: raise ApiError('Invalid password')
        account=User(username=phone,first_name=name)
        validate_password(password,account)
        account.set_password(password)
        account.save()
        login(request,account)
        return {'me':public_user(account)}
    if endpoint=='login':
        require_method(request,'POST')
        if not isinstance(body.get('password'),str) or len(body['password'])>128: raise ApiError('Invalid password')
        account=authenticate(request,username=text(body,'phone',150),password=body['password'])
        if account is None: raise ApiError('Wrong phone number / username or password',401)
        login(request,account)
        return {'me':public_user(account)}
    if endpoint=='logout':
        require_method(request,'POST'); logout(request); return {}
    if not user.is_authenticated: raise ApiError('Please log in',401)
    if endpoint=='taken':
        require_method(request,'GET')
        mv,day,show=show_details(request.GET)
        return {'seats':list(SeatReservation.objects.filter(movie=mv,date=day,time=show).values_list('seat',flat=True))}
    if endpoint=='book':
        require_method(request,'POST')
        mv,day,show=show_details(body)
        seats=body.get('seats')
        if not isinstance(seats,list) or not 1<=len(seats)<=10 or any(not isinstance(s,str) for s in seats) or len(set(seats))!=len(seats): raise ApiError('Choose 1 to 10 different seats')
        prices={f'{r}-{c}':cl.price for cl in TicketClass.objects.all() for r in cl.rows for c in range(1,cl.cols+1)}
        if any(s not in prices for s in seats): raise ApiError('Invalid seat')
        # Unique database constraint prevents concurrent double booking; all seats commit together.
        with transaction.atomic():
            booking=Booking.objects.create(user=user,movie=mv,movie_title=mv.title,date=day,time=show,seats=seats,amount=sum(prices[s] for s in seats))
            SeatReservation.objects.bulk_create([SeatReservation(booking=booking,movie=mv,date=day,time=show,seat=s) for s in seats])
        return {'booking':booking_data(booking)}
    if endpoint=='my-bookings':
        require_method(request,'GET')
        return {'bookings':[booking_data(b) for b in Booking.objects.filter(user=user).select_related('user').order_by('-created_at')]}
    if not endpoint.startswith('admin/'): raise ApiError('Not found',404)
    if not user.is_superuser: raise ApiError('Administrators only',403)
    if endpoint=='admin/bookings':
        require_method(request,'GET')
        return {'bookings':[booking_data(b) for b in Booking.objects.select_related('user').order_by('-created_at')]}
    match=re.fullmatch(r'admin/bookings/(BK[0-9A-F]{16})',endpoint)
    if match:
        require_method(request,'DELETE')
        Booking.objects.filter(ref=match[1]).delete()
        return {}
    if endpoint=='admin/movies':
        require_method(request,'POST')
        return {'movie':movie_data(Movie.objects.create(**clean_movie(body)))}
    match=re.fullmatch(r'admin/movies/(\d+)',endpoint)
    if match:
        if request.method not in ('PUT','DELETE'): raise ApiError('Method not allowed',405)
        try: mv=Movie.objects.get(pk=match[1],active=True)
        except Movie.DoesNotExist: raise ApiError('Movie not found',404)
        if request.method=='DELETE': mv.active=False
        else:
            data=clean_movie(body)
            # Existing reservations retain their show identifiers.
            removed=set(mv.times)-set(data['times'])
            if Booking.objects.filter(movie=mv,date__gte=timezone.localdate(),time__in=removed).exists(): raise ApiError('Cancel future bookings for removed show times before changing them')
            for k,v in data.items(): setattr(mv,k,v)
        mv.save(); return {}
    if endpoint=='admin/classes':
        require_method(request,'PUT')
        prices=body.get('prices',{})
        if not isinstance(prices,dict): raise ApiError('Invalid prices')
        with transaction.atomic():
            for cl in TicketClass.objects.all():
                if cl.name in prices:
                    v=str(prices[cl.name])
                    if not re.fullmatch(r'\d{1,4}',v) or int(v)>5000: raise ApiError('Enter whole-number prices between 0 and 5000')
                    cl.price=int(v); cl.save(update_fields=['price'])
        return {}
    if endpoint=='admin/upload':
        require_method(request,'POST')
        data=body.get('data','')
        if not isinstance(data,str) or len(data)>3_000_000 or not re.match(r'^data:image/(png|jpeg|webp);base64,',data): raise ApiError('Upload a PNG, JPG or WebP image under 2 MB')
        try:
            raw=base64.b64decode(data.split(',',1)[1],validate=True)
            with Image.open(io.BytesIO(raw)) as im:
                if im.width*im.height>16_000_000: raise ApiError('Image dimensions too large')
                im.load(); im.thumbnail((800,1200)); output=io.BytesIO(); im.convert('RGB').save(output,'JPEG',quality=88)
        except (ValueError,binascii.Error,UnidentifiedImageError,OSError,Image.DecompressionBombError): raise ApiError('Invalid image')
        name=default_storage.save('posters/'+uuid.uuid4().hex+'.jpg',ContentFile(output.getvalue()))
        return {'path':default_storage.url(name)}
    if endpoint=='admin/password':
        require_method(request,'PUT')
        if not isinstance(body.get('current'),str) or not user.check_password(body['current']): raise ApiError('Current password is wrong')
        pw=body.get('password','')
        if not isinstance(pw,str) or len(pw)>128: raise ApiError('Invalid password')
        validate_password(pw,user); user.set_password(pw); user.save(update_fields=['password']); update_session_auth_hash(request,user)
        return {}
    raise ApiError('Not found',404)
