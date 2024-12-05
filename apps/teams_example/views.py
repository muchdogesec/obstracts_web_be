from django.urls import reverse
from django.views.generic import (
    ListView,
    CreateView,
    UpdateView,
    DetailView,
    DeleteView,
)
from django.utils.translation import gettext_lazy as _

from .forms import PlayerForm
from .models import Player
from ..teams.mixins import LoginAndTeamRequiredMixin


class PlayerViewMixin(LoginAndTeamRequiredMixin):
    """
    Mixin class for all views in the example app.
    """

    model = Player

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["active_tab"] = "teams_example"
        context["page_title"] = _("Example App | {team}").format(team=self.request.team)
        return context


class PlayerListView(PlayerViewMixin, ListView):
    pass


class PlayerCreateView(PlayerViewMixin, CreateView):
    form_class = PlayerForm

    def form_valid(self, form):
        form.instance.team = self.request.team
        return super().form_valid(form)


class PlayerDetailView(PlayerViewMixin, DetailView):
    pass


class PlayerUpdateView(PlayerViewMixin, UpdateView):
    form_class = PlayerForm


class PlayerDeleteView(PlayerViewMixin, DeleteView):
    def get_success_url(self):
        return reverse("teams_example:player_list", args=[self.request.team.slug])
