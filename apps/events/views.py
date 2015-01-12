import csv
import logging
import random
import datetime

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.core.files import File
from django.core.urlresolvers import reverse, reverse_lazy
from django.forms import widgets
from django.forms.models import modelform_factory
from django.shortcuts import redirect, get_object_or_404

















# Create your views here.
from django.utils import timezone
from django.views.generic import ListView, DetailView, CreateView, UpdateView, \
    FormView, \
    DeleteView
from extra_views import UpdateWithInlinesView, CreateWithInlinesView
from form_utils.widgets import ImageWidget
from eestecnet.forms import DialogFormMixin
from apps.events.forms import DescriptionForm, EventImageInline, TransportForm, \
    UploadEventsForm, EventMixin, EventUpdateForm, EventCreationForm
from apps.events.models import Event, Application, Participation
from apps.teams.forms import ApplicationInline, ParticipationInline
from apps.teams.models import Team

logger = logging.getLogger(__name__)

class HTML5Input(widgets.Input):
    def __init__(self, type, attrs):
        self.input_type = type
        super(HTML5Input, self).__init__(attrs)


def featuredevent():
    try:
        random_idx = random.randint(0, Event.objects.filter(scope="international",
                                                            start_date__gt=datetime
                                                            .date.today()).exclude(
            category='recruitment').count() - 1)
        random_event = Event.objects.filter(
            scope="international", start_date__gt=datetime.date.today()).exclude(
            category='recruitment')[random_idx]
    except:
        random_event = Event.objects.filter(category="workshop").latest('start_date')
    return random_event


class AddEvents(FormView):
    form_class = UploadEventsForm
    template_name = "events/add_events.html"
    success_url = "/"

    def form_valid(self, form):
        self.handle_events(self.request.FILES['file'])
        return super(AddEvents, self).form_valid(form)

    def get_context_data(self, **kwargs):
        context = super(AddEvents, self).get_context_data(**kwargs)
        context['object'] = self.request.user
        return context

    def handle_events(self, f):
        eventreader = csv.reader(f)
        for event in eventreader:
            messages.success(self.request, " ".join([item for item in event]))
            try:
                t_oc = Team.objects.get(name=event[4])
            except:
                messages.success(self.request, "Cant find team " + event[4])
            t_oc = Team.objects.get(name=event[4])
            new_event = Event.objects.create(
                name=event[0] + "tempobject" + str(random.randint(1, 50000)),
                deadline=event[1],
                start_date=event[2],
                end_date=event[3],
                category=event[5],
                description=event[6],
                scope=event[8],
                max_participants=event[9],
            )
            new_event.save()
            new_event.organizers.add(self.request.user)
            new_event.organizing_committee.add(t_oc)
            if new_event.category == "training":
                if "ommunication" in new_event.name:
                    thumbname = "communication-skills.jpg"
                elif "motional" in new_event.name:
                    thumbname = "emotional-intelligence.jpg"
                elif "eedback" in new_event.name:
                    thumbname = "feedback.jpg"
                elif "resentation" in new_event.name:
                    thumbname = "presentation-skills.jpg"
                elif "rganizational" in new_event.name:
                    thumbname = "organizational-management.jpg"
                elif "eadership" in new_event.name:
                    thumbname = "leadership.jpg"
                elif "roject" in new_event.name:
                    thumbname = "project-management.jpg"
                elif "ime" in new_event.name and "anagement" in new_event.name:
                    thumbname = "time-management.jpg"
                elif "eambuilding" in new_event.name:
                    thumbname = "teambuilding.JPG"
                elif "acilitation" in new_event.name:
                    thumbname = "facilitation.jpg"
                elif "ynamics" in new_event.name:
                    thumbname = "group-dynamics.jpg"
                elif "ody" in new_event.name and "anguage" in new_event.name:
                    thumbname = "body-language.jpg"
                else:
                    thumbname = "trtlogo.png"
                with open('eestecnet/training/' + thumbname, 'rb') as doc_file:
                    new_event.thumbnail.save("thumbname.jpg", File(doc_file), save=True)
                randstring = ""
                try:
                    Event.objects.get(name=event[0] + "-" + str(new_event.start_date))
                    randstring = str(random.randint(1, 500))
                except:
                    pass
                new_event.name = event[0] + "-" + str(new_event.start_date) + randstring
            else:
                new_event.name = event[0]
            new_event.save()


class InternationalEvents(ListView):
    model = Event

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super(InternationalEvents, self).get_context_data(**kwargs)
        # Add in a QuerySet of all the books
        events = context['object_list'].filter(scope="international")
        context['active_list'] = []
        context['pending_list'] = []
        context['over_list'] = []
        for event in events:
            try:
                if event.deadline:
                    if event.deadline > timezone.now():
                        context['active_list'].append(event)
                    if event.deadline < timezone.now() and event.end_date > timezone \
                            .now() \
                            .date():
                        context['pending_list'].append(event)
                if event.end_date < timezone.now().date():
                    context['over_list'].append(event)
            except:
                pass
        return context


def confirm_event(request, slug):
    try:
        pa = Participation.objects.get(target__slug=slug, participant=request.user)
    except:
        return redirect(reverse('event', kwargs={'slug': slug}))
    pa.confirmed = True
    pa.confirmation = 0
    pa.save()
    logger.info(
        str(pa.participant) + " just confirmed their participation to " + str(pa.target))
    return redirect(reverse('event', kwargs={'slug': slug}))


class EventDetail(DetailView):
    model = Event
    template_name = "events/event_detail.html"

    def get_context_data(self, **kwargs):

        context = super(EventDetail, self).get_context_data(**kwargs)
        if self.get_object().deadline:
            context['applicable'] = timezone.now() < self.get_object().deadline
        else:
            context['applicable'] = timezone.now().date() <= self.get_object().start_date
        try:
            context['participation'] = Participation.objects.get(
                target__slug=self.kwargs['slug'], participant=self.request.user)
        except:
            context['participation'] = None
        return context


class DeleteApplication(DialogFormMixin, DeleteView):
    protected = 1
    model = Application

    def get_object(self, queryset=None):
        event = Event.objects.get(slug=self.kwargs['slug'])
        return Application.objects.get(applicant=self.request.user, target=event)

    def get_context_data(self, **kwargs):
        context = super(DeleteApplication, self).get_context_data(**kwargs)
        context['object'] = Event.objects.get(slug=self.kwargs['slug'])
        return context

    def post(self, request, *args, **kwargs):
        self.get_object().delete()
        return redirect(reverse('event', kwargs=self.kwargs))


class EditApplication(EventMixin, DialogFormMixin, UpdateView):
    protected = 1
    model = Application
    form_class = modelform_factory(Application, fields=["letter"])

    def get_object(self, queryset=None):
        event = Event.objects.get(slug=self.kwargs['slug'])
        return Application.objects.get(applicant=self.request.user, target=event)

    def get_context_data(self, **kwargs):
        context = super(EditApplication, self).get_context_data(**kwargs)
        context['object'] = Event.objects.get(slug=self.kwargs['slug'])
        return context


class ApplyToEvent(EventMixin, DialogFormMixin, CreateView):
    protected = 1
    model = Application
    form_class = modelform_factory(Application, fields=["letter"])
    submit = "Apply"

    def get_context_data(self, **kwargs):
        context = super(ApplyToEvent, self).get_context_data(**kwargs)
        context['object'] = Event.objects.get(slug=self.kwargs['slug'])
        return context

    def dispatch(self, request, *args, **kwargs):
        try:
            Application.objects.get(
                applicant=request.user,
                target=Event.objects.get(slug=self.kwargs['slug']))
            return redirect(self.get_success_url())
        except:
            return super(ApplyToEvent, self).dispatch(request, *args, **kwargs)


    def get_success_url(self):
        return reverse('event', kwargs=self.kwargs)

    def form_valid(self, form):
        application = form.save(commit=False)
        application.applicant = self.request.user
        application.target = Event.objects.get(slug=self.kwargs['slug'])
        if application.target.deadline:
            if timezone.now() > application.target.deadline:
                messages.add_message(
                    self.request,
                    messages.INFO,
                    'We are sorry. The deadline for this event has passed.')
                return redirect(self.get_success_url())

        application.save()
        messages.add_message(
            self.request,
            messages.INFO,
            'Thank you for your application. You will be notified upon acceptance.')

        logger.info(
            str(self.request.user) + " just applied to " + str(application.target))
        return redirect(self.get_success_url())


class UpdateTransport(EventMixin, DialogFormMixin, UpdateView):
    protected = 0
    form_class = TransportForm

    def get_object(self, queryset=None):
        return Participation.objects.get(applicant=self.request.user,
                                         target=Event.objects.get(
                                             slug=self.kwargs['slug'])).transportation


class FillInTransport(EventMixin, DialogFormMixin, CreateView):
    protected = 0
    form_class = TransportForm

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super(FillInTransport, self).get_context_data(**kwargs)
        # Add in a QuerySet of all the books
        context['object'] = Event.objects.get(slug=self.kwargs['slug'])
        return context

    def form_valid(self, form):
        if not self.request.user.tshirt_size or not self.request.user.profile_picture:
            return redirect(reverse('event', kwargs=self.kwargs))
        pax = get_object_or_404(Participation, participant=self.request.user,
                                target__slug=self.kwargs['slug'])
        trans = form.save()
        pax.transportation = trans
        pax.save()
        messages.add_message(
            self.request,
            messages.INFO,
            'Thank you for filling in your transportation details.')
        return redirect(reverse('event', kwargs=self.kwargs))


class ChangeDetails(EventMixin, DialogFormMixin, UpdateView):
    model = Event
    form_class = EventUpdateForm

    def action(self):
        return reverse_lazy("eventchangedetails", kwargs=self.kwargs)


class ChangeDescription(EventMixin, DialogFormMixin, UpdateView):
    form_class = DescriptionForm
    model = Event
    template_name = "events/description.html"


class EventImages(EventMixin, DialogFormMixin, UpdateWithInlinesView):
    model = Event
    form_class = modelform_factory(Event, fields=('thumbnail',),
                                   widgets={'thumbnail': ImageWidget()})
    inlines = [EventImageInline]

    def action(self):
        return reverse_lazy("eventimages", kwargs=self.kwargs)


class IncomingApplications(EventMixin, DialogFormMixin, UpdateWithInlinesView):
    model = Event
    fields = ()
    inlines = [ApplicationInline]
    form_title = "These people want to participate in the event!"

    def action(self):
        return reverse_lazy("eventapplications", kwargs=self.kwargs)


class Participations(EventMixin, DialogFormMixin, UpdateWithInlinesView):
    model = Event
    fields = ()
    inlines = [ParticipationInline]
    form_title = "These people want to participate in the event!"



class CreateEvent(DialogFormMixin, CreateWithInlinesView):
    model = Event
    form_class = EventCreationForm
    form_title = "Please fill in this form"
    action = reverse_lazy("create_event")
    form_id="createeventform"
    inlines = [EventImageInline]
    parent_template = "events/event_list.html"
    protected = 0
    additional_context = {"appendix":""" <script type="text/javascript">
        $(function () {
            $("input[type=submit]").button();
        });
    </script>"""}
    submit = "Create Event"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.has_perm('events.add_event'):
            raise PermissionDenied
        return super(CreateEvent, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(CreateEvent, self).get_context_data(**kwargs)
        assert (context["form"])
        return context
    def get_success_url(self):
        return reverse_lazy("events")
    def get_form_kwargs(self):
        kwargs = super(CreateEvent, self).get_form_kwargs()
        kwargs['user'] = self.request.user
        kwargs['teams'] = self.request.user.teams_administered()
        return kwargs



