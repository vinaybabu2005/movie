from django.contrib import admin
from .models import Movie, TicketClass, Booking
admin.site.site_header = 'Movie Booking Administration'
@admin.register(Movie)
class MovieAdmin(admin.ModelAdmin):
    list_display = ['title','lang','active']
    search_fields = ['title']
    readonly_fields = ['times','poster']
    def has_add_permission(self,request): return False
    def has_delete_permission(self,request,obj=None): return False
@admin.register(TicketClass)
class TicketClassAdmin(admin.ModelAdmin):
    list_display = ['name','price']
    readonly_fields = ['name','cols','rows']
    def has_add_permission(self,request): return False
    def has_delete_permission(self,request,obj=None): return False
@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ['ref','user','movie_title','date','time','amount','created_at']
    search_fields = ['ref','user__username','user__first_name','movie_title']
    list_filter = ['date','movie']
    readonly_fields = ['ref','user','movie','movie_title','date','time','seats','amount','created_at']
    def has_add_permission(self,request): return False
