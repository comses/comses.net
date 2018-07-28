from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import CreateView

from conference.forms import Submission2018Form


class Submission2018View(LoginRequiredMixin, CreateView):
    template_name = 'conference/submission.jinja'
    form_class = Submission2018Form
    success_url = '/'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs().copy()
        if self.request.POST:
            data = kwargs['data'].copy()
            data['author'] = self.request.user.member_profile.id
            kwargs['data'] = data
        return kwargs
