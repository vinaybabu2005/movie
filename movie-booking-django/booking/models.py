import uuid
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator

def reference():
    return 'BK' + uuid.uuid4().hex[:16].upper()

class Movie(models.Model):
    title = models.CharField(max_length=80)
    lang = models.CharField(max_length=30, default='Telugu')
    genre = models.CharField(max_length=40, blank=True)
    poster = models.CharField(max_length=250, blank=True)
    times = models.JSONField(default=list)
    active = models.BooleanField(default=True)
    def __str__(self): return self.title

class TicketClass(models.Model):
    name = models.CharField(max_length=40, unique=True)
    price = models.PositiveIntegerField(validators=[MaxValueValidator(5000)])
    cols = models.PositiveIntegerField(validators=[MinValueValidator(1),MaxValueValidator(20)])
    rows = models.JSONField(default=list)
    def __str__(self): return self.name

class Booking(models.Model):
    ref = models.CharField(max_length=18, unique=True, default=reference, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    movie = models.ForeignKey(Movie, on_delete=models.PROTECT)
    movie_title = models.CharField(max_length=80)
    date = models.DateField()
    time = models.CharField(max_length=8)
    seats = models.JSONField(default=list)
    amount = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self): return self.ref

class SeatReservation(models.Model):
    booking = models.ForeignKey(Booking,on_delete=models.CASCADE)
    movie = models.ForeignKey(Movie,on_delete=models.PROTECT)
    date = models.DateField()
    time = models.CharField(max_length=8)
    seat = models.CharField(max_length=10)
    class Meta:
        constraints = [models.UniqueConstraint(fields=['movie','date','time','seat'],name='unique_show_seat')]
