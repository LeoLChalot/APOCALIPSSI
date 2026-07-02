"""
Modèles de l'app accounts.

[Note pédagogique] On garde le modèle User standard de Django (simple et
robuste), et on lui ajoute un Profil 1-pour-1 pour les infos métier qui ne sont
pas dans User — ici `email_verified` (l'utilisateur a-t-il cliqué le lien de
confirmation envoyé par email ?).

Choix d'architecture « email = identifiant » : à l'inscription, on met
username = email (voir SignupSerializer). Le login se fait donc par email, sans
backend d'authentification custom. C'est le compromis le plus simple pour un
kit pédagogique (un vrai produit utiliserait souvent un User personnalisé avec
USERNAME_FIELD = 'email').
"""

from django.conf import settings
from django.db import models


class Profile(models.Model):
    """Informations complémentaires attachées à un utilisateur."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    # Validation "soft" : le compte fonctionne même si l'email n'est pas vérifié,
    # mais un bandeau invite l'utilisateur à cliquer le lien de confirmation.
    email_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"Profile<{self.user.email or self.user.username}>"


def get_or_create_profile(user) -> Profile:
    """Récupère (ou crée) le profil d'un utilisateur.

    Pratique pour les comptes créés AVANT l'ajout du modèle Profile (ils n'ont
    pas encore de profil) : on le crée à la volée plutôt que de planter.
    """
    profile, _ = Profile.objects.get_or_create(user=user)
    return profile


class DataRequest(models.Model):
    """Audit trail des demandes RGPD (SAR — Subject Access Request).

    [Note pédagogique] Les endpoints d'export (Art. 15/20) et d'effacement
    (Art. 17) *exécutent* la demande, mais sans en garder de trace : impossible
    ensuite de prouver qu'on a bien respecté le RGPD. Ce modèle journalise chaque
    demande pour la conformité (audit, litige, contrôle CNIL).

    Choix `on_delete=SET_NULL` + `requester_email` : la trace doit survivre à la
    suppression du compte (cas de l'effacement Art. 17). On garde donc l'email en
    clair comme identifiant de secours quand la FK `requester` devient NULL.
    """

    class RequestType(models.TextChoices):
        EXPORT = "export", "Export (Art. 15 / 20)"
        ERASE = "erase", "Effacement (Art. 17)"

    class Status(models.TextChoices):
        RECEIVED = "received", "Reçue"
        IN_PROGRESS = "in_progress", "En cours"
        ANSWERED = "answered", "Répondue"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="data_requests",
    )
    # Identifiant de secours : survit à la suppression du compte (Art. 17).
    user_email = models.EmailField(blank=True)
    request_type = models.CharField(max_length=10, choices=RequestType.choices)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.RECEIVED,
    )
    requested_at = models.DateTimeField(auto_now_add=True)
    answered_at = models.DateTimeField(null=True, blank=True)
    export_hash = models.CharField(max_length=64, blank=True)

    class Meta:
        ordering = ["-requested_at"]

    def __str__(self) -> str:
        who = self.user_email or (self.user and self.user.email) or "?"
        return f"DataRequest<{self.request_type} {who} {self.status}>"
