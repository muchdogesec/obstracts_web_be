from django.core.management.base import BaseCommand

from apps.teams.models import Team
from apps.teams.roles import is_admin
from apps.users.models import CustomUser


class Command(BaseCommand):
    help = "Migrates the Customer object from the CustomUser model to the Team model"

    def handle(self, **options):
        for user in CustomUser.objects.exclude(customer=None):
            if user.customer.subscriptions.count() == 1:
                user_subscription = user.customer.subscriptions.get()
                team = Team.objects.get(subscription=user_subscription)
                if is_admin(user, team):
                    if team.customer is None:
                        team.customer = user.customer
                        team.save()
                        print(f"Set customer {user.customer} on team {team}")
                    else:
                        print(
                            f"Did NOT set customer {user.customer} on team {team} because a customer ({team.customer}) is already set."
                        )
                else:
                    print(
                        f"Did NOT set customer {user.customer} on team {team} because they are not an admin."
                    )
            else:
                print(
                    f"Did NOT set customer {user.customer} on any team because they manage multiple subscriptions. "
                    "This must be resolved manually. Subscriptions:"
                )

                def _display(subscription):
                    try:
                        team = subscription.team_set.get()
                    except Team.DoesNotExist:
                        team = "-"
                    return f"Id: {subscription.id}, Team: {team}, Plan: {subscription.plan}"

                separator = "\n\t"
                print(
                    f"\t{separator.join([_display(s) for s in user.customer.subscriptions.all()])}"
                )
