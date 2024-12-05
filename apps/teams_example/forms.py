from django import forms

from apps.teams_example.models import Player


class PlayerForm(forms.ModelForm):
    class Meta:
        model = Player
        fields = ["name", "sex", "date_of_birth"]
