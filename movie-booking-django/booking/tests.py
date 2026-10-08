import json
from datetime import timedelta
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.core.management import call_command
from django.utils import timezone
from .models import Booking, SeatReservation, Movie, TicketClass

class BookingTests(TestCase):
    def setUp(self):
        call_command('seed_movies',verbosity=0)
        self.user=User.objects.create_user('9876543210',password='Example!Pass73',first_name='Test Customer')
        self.admin=User.objects.create_superuser('manager',password='Example!Admin73')
        self.client.force_login(self.user)
        self.data={'movieId':Movie.objects.first().pk,'date':(timezone.localdate()+timedelta(days=1)).isoformat(),'time':'10:00 AM','seats':['1-1','7-1'],'amount':1}
    def send(self,path,data=None,method='post',client=None):
        return getattr(client or self.client,method)('/api/'+path,data=json.dumps(data or {}),content_type='application/json')
    def test_booking_prices_privacy_and_duplicate_rollback(self):
        response=self.send('book',self.data)
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.json()['booking']['amount'],350)
        self.assertEqual(SeatReservation.objects.count(),2)
        self.assertEqual(self.send('book',{**self.data,'seats':['1-2','1-1']}).status_code,409)
        self.assertEqual(Booking.objects.count(),1)
        self.assertEqual(SeatReservation.objects.count(),2)
        other=Client(); other.force_login(User.objects.create_user('9876543211',password='Another!Pass73'))
        self.assertEqual(other.get('/api/my-bookings').json()['bookings'],[])
        self.assertEqual(other.get('/api/admin/bookings').status_code,403)
    def test_cancel_frees_seats(self):
        ref=self.send('book',self.data).json()['booking']['ref']
        self.assertEqual(self.send('admin/bookings/'+ref,method='delete').status_code,403)
        self.client.force_login(self.admin)
        self.assertEqual(self.send('admin/bookings/'+ref,method='delete').status_code,200)
        self.assertFalse(SeatReservation.objects.exists())
        self.assertEqual(self.send('book',self.data).status_code,200)
    def test_registration_login_logout_and_csrf(self):
        client=Client(enforce_csrf_checks=True)
        self.assertEqual(self.send('register',{},client=client).status_code,403)
        self.assertEqual(client.get('/').status_code,200)
        token=client.cookies['csrftoken'].value
        data={'name':'Vinay','phone':'9876543212','password':'Unusual!Pass73'}
        response=client.post('/api/register',json.dumps(data),content_type='application/json',HTTP_X_CSRFTOKEN=token)
        self.assertEqual(response.status_code,200)
        user=User.objects.get(username=data['phone']); self.assertTrue(user.check_password(data['password']))
        self.assertNotEqual(user.password,data['password'])
        token=client.cookies['csrftoken'].value
        self.assertEqual(client.post('/api/logout','{}',content_type='application/json',HTTP_X_CSRFTOKEN=token).status_code,200)
        self.assertIsNone(client.get('/api/config').json()['me'])
        self.assertEqual(client.post('/api/login',json.dumps(data),content_type='application/json',HTTP_X_CSRFTOKEN=token).status_code,200)
    def test_invalid_seats_date_method_and_anonymous(self):
        for patch in [{'seats':['99-99']},{'seats':[]},{'date':'2020-01-01'},{'time':'Bad'}]:
            self.assertEqual(self.send('book',{**self.data,**patch}).status_code,400)
        self.assertEqual(self.client.get('/api/book').status_code,405)
        self.assertEqual(Client().get('/api/my-bookings').status_code,401)
    def test_admin_movies_prices_password_and_users(self):
        self.client.force_login(self.admin)
        data={'title':'New Movie','lang':'Telugu','times':'9:00 AM, 6:00 PM','poster':''}
        response=self.send('admin/movies',data); self.assertEqual(response.status_code,200)
        mid=response.json()['movie']['id']
        self.assertEqual(self.send(f'admin/movies/{mid}',{**data,'title':'Edited'},'put').status_code,200)
        self.assertEqual(self.send('admin/classes',{'prices':{'First Class':'160'}},'put').status_code,200)
        self.assertEqual(TicketClass.objects.get(name='First Class').price,160)
        self.assertEqual(self.send('admin/password',{'current':'Example!Admin73','password':'Changed!Secret73'},'put').status_code,200)
        self.assertEqual(self.client.get('/admin/auth/user/').status_code,200)
        self.assertEqual(self.send(f'admin/movies/{mid}',method='delete').status_code,200)
        self.assertFalse(Movie.objects.get(pk=mid).active)
    def test_seed_is_idempotent_and_pages(self):
        call_command('seed_movies',verbosity=0)
        self.assertEqual(Movie.objects.count(),5)
        self.assertEqual(TicketClass.objects.count(),4)
        self.assertContains(self.client.get('/'),'/static/app.js')
        self.assertEqual(Client().get('/admin/').status_code,302)
