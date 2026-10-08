from django.core.management.base import BaseCommand
from booking.models import Movie, TicketClass
class Command(BaseCommand):
    help='Add the original five movies and seat classes without resetting existing data'
    def handle(self,*args,**options):
        movies=[('The Paradise','paradise',['10:00 AM','1:30 PM','6:30 PM','10:00 PM']),('Peddi','peddi',['10:30 AM','2:00 PM','6:00 PM','9:45 PM']),('Ranabaali','ranabaali',['11:00 AM','2:30 PM','7:00 PM','10:15 PM']),('Jailer 2','jailer2',['10:00 AM','1:15 PM','6:15 PM','9:30 PM']),('Doomsday','doomsday',['12:00 PM','3:30 PM','8:00 PM'])]
        for title,image,times in movies:
            Movie.objects.get_or_create(title=title,defaults={'poster':f'/static/images/{image}.png','times':times})
        for name,price,cols,rows in [('First Class',150,12,['1','2','3']),('Second Class',120,12,['4','5','6']),('Balcony',200,12,['7','8','9']),('Recliner',400,6,['10','11'])]:
            TicketClass.objects.get_or_create(name=name,defaults={'price':price,'cols':cols,'rows':rows})
        self.stdout.write(self.style.SUCCESS('Movies and seat classes are ready.'))
