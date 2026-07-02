"""Tests pédagogiques pour l'app accounts.

Ces tests servent d'exemples : signup, login, logout, accès protégé.
Lancez : pytest accounts/
"""

import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db


@pytest.fixture
def client() -> APIClient:
    return APIClient()


@pytest.fixture
def user(db) -> User:
    return User.objects.create_user(
        username="alice", email="alice@test.com", password="motdepasse123"
    )


def test_signup_creates_user(client):
    # Lot 3 : inscription par EMAIL (username = email en interne).
    response = client.post(
        "/api/accounts/signup/",
        {
            "email": "bob@test.com",
            "password": "motdepasse123",
        },
        format="json",
    )
    assert response.status_code == 201, response.data
    assert User.objects.filter(email="bob@test.com").exists()


def test_signup_requires_email(client):
    response = client.post(
        "/api/accounts/signup/",
        {"password": "motdepasse123"},
        format="json",
    )
    assert response.status_code == 400


def test_login_returns_token(client, user):
    response = client.post(
        "/api/accounts/login/",
        {"email": "alice@test.com", "password": "motdepasse123"},
        format="json",
    )
    assert response.status_code == 200, response.data
    assert "token" in response.data
    assert response.data["user"]["email"] == "alice@test.com"


def test_login_with_wrong_password(client, user):
    response = client.post(
        "/api/accounts/login/",
        {"email": "alice@test.com", "password": "wrong"},
        format="json",
    )
    assert response.status_code == 400


def test_me_requires_auth(client):
    response = client.get("/api/accounts/me/")
    assert response.status_code in (401, 403)


def test_me_with_token(client, user):
    from rest_framework.authtoken.models import Token

    token = Token.objects.create(user=user)
    client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    response = client.get("/api/accounts/me/")
    assert response.status_code == 200
    assert response.data["username"] == "alice"


def test_logout_invalidates_token(client, user):
    from rest_framework.authtoken.models import Token

    token = Token.objects.create(user=user)
    client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    response = client.post("/api/accounts/logout/")
    assert response.status_code == 204
    # Le token n'existe plus
    assert not Token.objects.filter(key=token.key).exists()


# ---------------------------------------------------------------------------
# RGPD — Tests SAR (Art. 15, 17, 20)
# ---------------------------------------------------------------------------


@pytest.fixture
def auth_client(user) -> APIClient:
    from rest_framework.authtoken.models import Token

    token = Token.objects.create(user=user)
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    return c


def test_gdpr_export_requires_auth(client):
    response = client.get("/api/accounts/gdpr/export/")
    assert response.status_code in (401, 403)


def test_gdpr_export_returns_user_data(auth_client, user):
    """Art. 15 + Art. 20 : l'export contient les données personnelles en JSON."""
    response = auth_client.get("/api/accounts/gdpr/export/")
    assert response.status_code == 200
    data = response.data
    assert "metadata" in data
    assert data["metadata"]["export_format"] == "JSON"
    assert "user" in data
    assert data["user"]["email"] == "alice@test.com"
    assert "quizzes" in data


def test_gdpr_export_includes_quizzes(auth_client, user):
    """Art. 15 : l'export inclut les quiz et leurs questions."""
    from quizzes.models import Question, Quiz

    quiz = Quiz.objects.create(user=user, title="Test RGPD", source_text="Contenu")
    Question.objects.create(
        quiz=quiz, index=1, prompt="Q1 ?",
        options=["A", "B", "C", "D"], correct_index=0,
    )

    response = auth_client.get("/api/accounts/gdpr/export/")
    assert response.status_code == 200
    assert len(response.data["quizzes"]) == 1
    assert response.data["quizzes"][0]["title"] == "Test RGPD"
    assert len(response.data["quizzes"][0]["questions"]) == 1


def test_gdpr_erase_requires_auth(client):
    response = client.delete("/api/accounts/gdpr/erase/")
    assert response.status_code in (401, 403)


def test_gdpr_erase_requires_password(auth_client):
    """Art. 17 : l'effacement exige la confirmation par mot de passe."""
    response = auth_client.delete(
        "/api/accounts/gdpr/erase/",
        {"password": "wrong"},
        format="json",
    )
    assert response.status_code == 400


def test_gdpr_erase_deletes_all_data(auth_client, user):
    """Art. 17 : l'effacement supprime le compte + toutes les données."""
    from quizzes.models import Quiz

    Quiz.objects.create(user=user, title="À supprimer", source_text="X")

    response = auth_client.delete(
        "/api/accounts/gdpr/erase/",
        {"password": "motdepasse123"},
        format="json",
    )
    assert response.status_code == 204
    assert not User.objects.filter(pk=user.pk).exists()
    assert Quiz.objects.filter(user=user).count() == 0


# ---------------------------------------------------------------------------
# RGPD — Audit trail des demandes (modèle DataRequest)
# ---------------------------------------------------------------------------


def test_export_creates_audit_trail(auth_client, user):
    """Un export doit laisser une trace DataRequest (type export, répondue)."""
    from accounts.models import DataRequest

    auth_client.get("/api/accounts/gdpr/export/")

    req = DataRequest.objects.get(user=user, request_type=DataRequest.RequestType.EXPORT)
    assert req.status == DataRequest.Status.ANSWERED
    assert req.user_email == "alice@test.com"
    assert req.answered_at is not None
    # L'empreinte SHA-256 est un hex de 64 caractères.
    assert len(req.export_hash) == 64


def test_each_export_is_independently_traced(auth_client, user):
    """Chaque export laisse SA propre trace (le fichier remis est horodaté, donc
    distinct à chaque fois) : deux exports => deux DataRequest, deux empreintes."""
    from accounts.models import DataRequest

    auth_client.get("/api/accounts/gdpr/export/")
    auth_client.get("/api/accounts/gdpr/export/")

    hashes = list(
        DataRequest.objects.filter(
            user=user, request_type=DataRequest.RequestType.EXPORT
        ).values_list("export_hash", flat=True)
    )
    assert len(hashes) == 2
    # Chaque empreinte est un SHA-256 valide (64 caractères hexadécimaux).
    assert all(len(h) == 64 for h in hashes)


def test_erase_creates_surviving_audit_trail(auth_client, user):
    """Un effacement laisse une trace qui SURVIT à la suppression du compte.

    La FK `user` passe à NULL (on_delete=SET_NULL) mais la ligne reste,
    identifiée par `user_email` — c'est la preuve de conformité Art. 17.
    """
    from accounts.models import DataRequest

    auth_client.delete(
        "/api/accounts/gdpr/erase/",
        {"password": "motdepasse123"},
        format="json",
    )

    assert not User.objects.filter(pk=user.pk).exists()
    req = DataRequest.objects.get(request_type=DataRequest.RequestType.ERASE)
    assert req.user is None  # FK vidée par SET_NULL
    assert req.user_email == "alice@test.com"  # mais l'identité est conservée
    assert req.status == DataRequest.Status.ANSWERED
    assert req.export_hash == ""  # aucun fichier remis lors d'un effacement
