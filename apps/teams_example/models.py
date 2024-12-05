from django.db import models
from django.urls import reverse

from apps.teams.models import BaseTeamModel


class Player(BaseTeamModel):
    """
    A player is part of a team.

    Note that it inherits from BaseTeamModel which handles the team relationship.
    """

    SEX_CHOICES = (
        ("m", "Male"),
        ("f", "Female"),
    )
    name = models.CharField(max_length=100)
    sex = models.CharField(max_length=10, blank=True, choices=SEX_CHOICES)
    date_of_birth = models.DateField(null=True, blank=True, help_text="E.g. 1979-05-12")

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse(
            "teams_example:player_detail",
            kwargs={"team_slug": self.team.slug, "pk": self.pk},
        )
