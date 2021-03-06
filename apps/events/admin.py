import csv

from django import forms
from django.contrib import admin
from django.db.models import Q
from django.http import HttpResponse
from suit_redactor.widgets import RedactorWidget

from apps.account.models import Eestecer
from apps.events.models import Event, Application, EventImage, \
    Participation, IncomingApplication, OutgoingApplication, Transportation


class ApplicationInline(admin.TabularInline):
    model = Application
    readonly_fields = ["priority", "letter", "member_in", "gender"]
    fields = ["member_in", "priority", "letter", "gender", 'accepted']

    def has_add_permission(self, request):
        return False

    def gender(self, instance):
        return self.instace.applicant.gender


class ParticipationInline(admin.TabularInline):
    model = Participation
    verbose_name_plural = "Participants"
    readonly_fields = ["participant", "confirmed", "transportation"]

    def has_add_permission(self, request):
        return False


class ImageInline(admin.TabularInline):
    model = EventImage


class MyEventAdminForm(forms.ModelForm):
    class Meta:
        model = Event
        widgets = {
            'description': RedactorWidget(editor_options={'lang': 'en', 'iframe': 'true',
                                                          'css':
                                                              "/static/enet/css/wysiwyg.css"}),
        }


class MyEventAdmin(admin.ModelAdmin):
    """ Custom interface to administrate Events from the django admin interface. """
    form = MyEventAdminForm
    list_display = ['name', 'OC', 'start_date']
    list_filter = ['category', 'organizing_committee']
    inlines = [ImageInline, ParticipationInline]
    filter_horizontal = ["organizers", "organizing_committee"]
    """ Inline interface for displaying the applications to an event and making it
    possible to accept them"""
    exclude = ['participants', "participant_count"]
    fieldsets = (
        ('Basic Event Information', {
            'fields': (
                ('name', 'category'), ('scope'),  ('description'),
                ('participation_fee', 'max_participants'), 'thumbnail'
            )
        }),
        ('Organizers', {
            'fields': (('organizers'),)
        }),
        ('Organizing Committees', {
            'fields': (('organizing_committee'),)
        }),
        ('Dates', {
            'fields': (('start_date', 'end_date', 'deadline', 'location'),)
        }),
        ('Reports', {
            'classes': ('collapse',),
            'fields': (('organizer_report', 'pax_report'),)
        })
    )
    add_fieldsets = (
        ('Basic Event Information', {
            'fields': (
                ('name', 'category', 'scope'),( 'description',),
                ('participation_fee', 'max_participants'), 'thumbnail'
            )
        }),
        ('Organizers', {
            'fields': (('organizing_committee',), ('organizers'),)
        }),
        ('Dates', {
            'fields': (('start_date', 'end_date', 'deadline'),)
        }),
    )

    def get_queryset(self, request):
        """ A Local admin will only be able to modify :class:`Event`s that he has
        privileges for.
        Admins still get to see all events. Organizers of events get to see their own
        evens. """
        qs = super(MyEventAdmin, self).get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(
            Q(organizing_committee__in=request.user.teams_administered()) | Q(
                organizers=request.user))


class OutgoingApplicationFilter(admin.SimpleListFilter):
    title = "Events"
    parameter_name = 'target'

    def lookups(self, request, model_admin):
        qs = model_admin.get_queryset(request)
        events = set([application.target for application in qs])
        for event in events:
            yield (event, event)

    def queryset(self, request, queryset):
        return queryset


class IncomingApplicationFilter(admin.SimpleListFilter):  #
    title = "Events"
    parameter_name = 'target'

    def lookups(self, request, model_admin):
        qs = model_admin.get_queryset(request)
        events = set([application.target for application in qs])
        for event in events:
            yield (event, event)

    def queryset(self, request, queryset):
        return queryset


def get_own_members(request):
    try:
        return \
        request.user.teams_administered().filter(category__in=['observer', 'jlc', 'lc'])[
        0].users.all()
    except IndexError:
        return Eestecer.objects.none()


class OutgoingApplicationAdmin(admin.ModelAdmin):
    """ Custom interface to administrate Events from the django admin interface. """
    list_display = ['applicant', 'target', 'priority']
    list_editable = ['priority']
    readonly_fields = ['letter', 'target', 'applicant', 'accepted']
    list_filter = [OutgoingApplicationFilter, ]

    def get_queryset(self, request):
        """ A Local admin will only be able to modify applications issued by teams
        from their LC
        Admins still get to see all applications"""
        qs = super(OutgoingApplicationAdmin, self).get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(applicant__in=get_own_members(request))


class IncomingApplicationAdmin(admin.ModelAdmin):
    """ Custom interface to administrate Events from the django admin interface. """
    list_display = ['applicant', 'target', 'priority', 'accepted']
    list_editable = ['accepted']
    list_filter = [IncomingApplicationFilter]
    readonly_fields = ['letter', 'target', 'applicant', 'priority']
    #TODO Fieldsets

    def get_queryset(self, request):
        """ A Local admin will only be able to modify applications applying to an
        event by their LC
        Admins still get to see all applications"""
        qs = super(IncomingApplicationAdmin, self).get_queryset(request)
        if request.user.is_superuser:
            return qs
        try:
            qs = qs.filter(
                # They're either for an event by a committee administered by the user
                Q(target__in=request.user.teams_administered().filter(
                    type__in=['observer', 'jlc', 'lc'])[0].event_set.all()) |
                # Or directly for an event directly administered by the user
                Q(target__in=request.user.events_organized.all())
            )
        except:
            raise
            return qs.none()
        return qs


class TransportationInlineAdmin(admin.TabularInline):
    model = Transportation


class EventParticipationAdmin(admin.ModelAdmin):
    """ Custom interface to administrate Events from the django admin interface. """
    list_display = ['participant', 'e_mail', 'food', 't_shirt_size', 'confirmed',
                    'transportation_details_filled']
    list_filter = [IncomingApplicationFilter]
    actions = ['download_transportation_details', 'download_participant_details']

    def download_participant_details(self, request, queryset):
        import xlwt

        response = HttpResponse(content_type='application/ms-excel')
        response['Content-Disposition'] = 'attachment; filename=' + queryset[
            0].target.slug + 'ParticipantDetails.xls'
        wb = xlwt.Workbook(encoding='utf-8')
        ws = wb.add_sheet("TransportationDetails")

        row_num = 0

        columns = [
            (u"Full Name", 8000),
            (u"LC", 3000),
            (u"Email", 3000),
            (u"gender", 3000),
            (u"T Shirt Size", 6000),
            (u"Birthday", 6000),
            (u"Allergies", 3000),
            (u"Food Preferences", 4000),
        ]

        font_style = xlwt.XFStyle()
        font_style.font.bold = True

        for col_num in xrange(len(columns)):
            ws.write(row_num, col_num, columns[col_num][0], font_style)
            # set column width
            ws.col(col_num).width = columns[col_num][1]

        font_style = xlwt.XFStyle()
        font_style.alignment.wrap = 1

        for pax in queryset:
            row_num += 1
            row = [
                pax.participant.get_full_name(),
                ", ".join(str(person) for person in pax.participant.lc()),
                pax.participant.email,
                pax.participant.gender,
                pax.participant.tshirt_size,
                pax.participant.date_of_birth,
                pax.participant.allergies,
                pax.participant.food_preferences,
            ]

            for col_num in xrange(len(row)):
                ws.write(row_num, col_num, row[col_num], font_style)

        wb.save(response)
        return response

    def download_transportation_details(self, request, queryset):
        import xlwt

        response = HttpResponse(content_type='application/ms-excel')
        response['Content-Disposition'] = 'attachment; filename=' + queryset[
            0].target.slug + 'TransportationDetails.xls'
        wb = xlwt.Workbook(encoding='utf-8')
        ws = wb.add_sheet("TransportationDetails")

        row_num = 0

        columns = [
            (u"Full Name", 8000),
            (u"Arrival Date and Time", 6000),
            (u"Arrival By", 3000),
            (u"Arrival Number", 4000),
            (u"Departure Date and Time", 6000),
            (u"Depart By", 3000),
            (u"Comment", 10000),
        ]

        font_style = xlwt.XFStyle()
        font_style.font.bold = True

        for col_num in xrange(len(columns)):
            ws.write(row_num, col_num, columns[col_num][0], font_style)
            # set column width
            ws.col(col_num).width = columns[col_num][1]

        font_style = xlwt.XFStyle()
        font_style.alignment.wrap = 1

        for pax in queryset:
            row_num += 1
            row = [
                pax.participant.get_full_name(),
                str(pax.transportation.arrival),
                pax.transportation.arrive_by,
                pax.transportation.arrival_number,
                str(pax.transportation.departure),
                pax.transportation.depart_by,
            ]

            for col_num in xrange(len(row)):
                ws.write(row_num, col_num, row[col_num], font_style)

        wb.save(response)
        return response

    def download_transportation_details_csv(self, request,
                                            queryset):  #todo test  #todo pdf instead of csv
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="somefilename.csv"'
        writer = csv.writer(response)
        for pax in queryset:
            writer.writerow([pax.participant.get_full_name(),
                             pax.transportation.arrival,
                             pax.transportation.arrive_by,
                             pax.transportation.arrival_number,
                             pax.transportation.departure,
                             pax.transportation.depart_by])

        return response

    def transportation_details_filled(self, instance):
        if instance.transportation:
            return True
        return False

    #TODO Fieldsets
    def has_add_permission(self, request):
        return False

    def e_mail(self, instance):
        return instance.participant.email

    def food(self, instance):
        return instance.participant.food_preferences

    def t_shirt_size(self, instance):
        return instance.participant.tshirt_size

    def get_queryset(self, request):
        """ A Local admin will only be able to modify applications issued by teams
        from their LC
        Admins still get to see all applications"""
        qs = super(EventParticipationAdmin, self).get_queryset(request)
        #if request.user.is_superuser:
        #TODO sanity check
        if request.user.is_superuser:
            return qs
        try:
            return qs.filter(target__in=request.user.teams_administered().filter(
                type__in=['observer', 'jlc', 'lc'])[0].event_set.all())
        except:
            return qs.none()


admin.site.register(Event, MyEventAdmin)
admin.site.register(OutgoingApplication, OutgoingApplicationAdmin)
admin.site.register(IncomingApplication, IncomingApplicationAdmin)
admin.site.register(Application)
admin.site.register(Participation, EventParticipationAdmin)
