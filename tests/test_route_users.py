from pytest import mark
from fastapi import status
from sqlalchemy import select

from app.database.models import User, UserRole
from app.services.cloudinary import FORMAT_AVATAR


@mark.asyncio
class TestGetMy:
    url_path = "api/users/me/"

    @mark.usefixtures('mock_rate_limit')
    @mark.parametrize(
        "status_code, detail, authorization",
        (
                (status.HTTP_401_UNAUTHORIZED, "Not authenticated", None),
                (status.HTTP_401_UNAUTHORIZED, "Could not validate credentials", "invalid"),
        )
    )
    async def test_exceptions(self, client,
                              status_code, detail, authorization):
        if authorization == "invalid":
            headers = {"Authorization": "Bearer invalid_access_token"}
        else:
            headers = {}

        response = client.get(self.url_path, headers=headers)

        assert response.status_code == status_code
        assert response.json()['detail'] == detail

    @mark.usefixtures('mock_rate_limit')
    async def test_was_successfully(self, client, access_token, user):
        response = client.get(
            self.url_path,
            headers={"Authorization": f"Bearer {access_token}"}
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json()['email'] == user['email']


@mark.asyncio
class TestUpdateAvatar:
    url_path = "api/users/avatar"

    @mark.usefixtures('mock_rate_limit')
    @mark.parametrize(
        "status_code, detail, authorization",
        (
                (status.HTTP_401_UNAUTHORIZED, "Not authenticated", None),
                (status.HTTP_401_UNAUTHORIZED, "Could not validate credentials", "invalid"),
                (status.HTTP_422_UNPROCESSABLE_ENTITY, "Invalid image file", "valid"),
        )
    )
    async def test_exceptions(self, client, access_token, mocker,
                              status_code, detail, authorization):
        if authorization == "invalid":
            headers = {"Authorization": "Bearer invalid_access_token"}
        elif authorization == "valid":
            headers = {"Authorization": f"Bearer {access_token}"}
            mocker.patch("app.services.cloudinary.upload_image", return_value=None)
        else:
            headers = {}

        response = client.patch(
            self.url_path,
            files={"file": ("test.png", b"image", "image/png")},
            headers=headers,
        )

        assert response.status_code == status_code
        assert response.json()['detail'] == detail

    @mark.usefixtures('mock_rate_limit')
    async def test_was_successfully(self, client, access_token, user, mocker):
        mock_image = {
            "url": "https://res.cloudinary.com/dlwnuqx3p/image/upload/v1678785308/cld-sample-5",
            "public_id": "cld-sample-5",
            "version": "1678785308"
        }
        mock_format_image = {
            "url": "https://res.cloudinary.com/dlwnuqx3p/image/upload/c_fill,h_250,w_250/v1678785308/cld-sample-5",
            "format": FORMAT_AVATAR
        }
        mocker.patch("app.services.cloudinary.upload_image", return_value=mock_image)
        mocker.patch("app.services.cloudinary.formatting_image_url", return_value=mock_format_image)

        response = client.patch(
            self.url_path,
            files={"file": ("test.png", b"image", "image/png")},
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json()['email'] == user['email']
        assert response.json()['avatar'] == mock_format_image['url']


@mark.asyncio
class TestUpdateEmail:
    url_path = "api/users/email"

    @mark.usefixtures('mock_rate_limit')
    @mark.parametrize(
        "status_code, detail, authorization",
        (
                (status.HTTP_401_UNAUTHORIZED, "Not authenticated", None),
                (status.HTTP_401_UNAUTHORIZED, "Could not validate credentials", "invalid"),
        )
    )
    async def test_exceptions(self, client, access_token, user,
                              status_code, detail, authorization):
        if authorization == "invalid":
            headers = {"Authorization": "Bearer invalid_access_token"}
        else:
            headers = {}

        response = client.patch(
            self.url_path,
            json={"email": "update.email@test.com"},
            headers=headers,
        )

        assert response.status_code == status_code
        assert response.json()['detail'] == detail

    @mark.usefixtures('mock_rate_limit')
    async def test_was_successfully(self, client, access_token, user):
        user.update(email="update.email@test.com")

        response = client.patch(
            self.url_path,
            json={"email": user['email']},
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json()['email'] == user['email']


@mark.asyncio
class TestUpdatePassword:
    url_path = "api/users/password"

    @mark.usefixtures('mock_rate_limit')
    @mark.parametrize(
        "status_code, detail, authorization",
        (
                (status.HTTP_401_UNAUTHORIZED, "Not authenticated", None),
                (status.HTTP_401_UNAUTHORIZED, "Could not validate credentials", "invalid"),
                (status.HTTP_401_UNAUTHORIZED, "Invalid old password", "valid"),
        )
    )
    async def test_exceptions(self, client, access_token, user,
                              status_code, detail, authorization):
        if authorization == "invalid":
            headers = {"Authorization": "Bearer invalid_access_token"}
        elif authorization == "valid":
            headers = {"Authorization": f"Bearer {access_token}"}
        else:
            headers = {}

        response = client.patch(
            self.url_path,
            json={"old_password": "invalid", "new_password": "update_pwd"},
            headers=headers,
        )

        assert response.status_code == status_code
        assert response.json()['detail'] == detail

    @mark.usefixtures('mock_rate_limit')
    async def test_was_successfully(self, client, access_token, user):
        new_password = "update_pwd"

        response = client.patch(
            self.url_path,
            json={"old_password": user['password'], "new_password": new_password},
            headers={"Authorization": f"Bearer {access_token}"},
        )

        user.update(password=new_password)

        assert response.status_code == status.HTTP_200_OK
        assert response.json()['email'] == user['email']


@mark.asyncio
class TestChangeRole:
    url_path = "api/users/change-role"
    new_user = {}

    async def test_was_successfully(self, client, access_token, user):
        TestChangeRole.new_user = user.copy()
        TestChangeRole.new_user['username'] = "new_user"
        TestChangeRole.new_user['email'] = "new.email@test.com"

        response = client.post("/api/auth/signup", json=self.new_user)

        TestChangeRole.new_user.update({"id": response.json()['user']['id']})

        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()['user']['email'] == self.new_user['email']
        assert response.json()['user']['role'] == UserRole.user

        response = client.post(
            self.url_path,
            headers={"Authorization": f"Bearer {access_token}"},
            json={"user_id": self.new_user['id'], "role": UserRole.moderator}
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json()['email'] == self.new_user['email']
        assert response.json()['role'] == UserRole.moderator

    @mark.usefixtures('mock_rate_limit')
    @mark.parametrize(
        "status_code, detail, authorization, role",
        (
                (status.HTTP_401_UNAUTHORIZED, "Not authenticated", None, UserRole.user),
                (status.HTTP_401_UNAUTHORIZED, "Could not validate credentials", "invalid", UserRole.user),
                (status.HTTP_404_NOT_FOUND, "User not found", "valid", UserRole.user),
                (status.HTTP_400_BAD_REQUEST, "This user already has this role installed", "valid", UserRole.moderator),
                (status.HTTP_403_FORBIDDEN, "Access denied. Access open to \"moderator\"", "valid", UserRole.moderator),
        )
    )
    async def test_exceptions(self, client, access_token, user, session,
                              status_code, detail, authorization, role):
        if status_code == status.HTTP_403_FORBIDDEN:
            current_user: User = await session.scalar(select(User).filter(User.email == user['email']))
            current_user.role = "moderator"
            await session.commit()

        if authorization == "invalid":
            headers = {"Authorization": "Bearer invalid_access_token"}
        elif authorization == "valid":
            headers = {"Authorization": f"Bearer {access_token}"}
        else:
            headers = {}

        response = client.post(
            self.url_path,
            json={
                "user_id": self.new_user['id'] if role == UserRole.moderator else 0,
                "role": role
            },
            headers=headers,
        )

        assert response.status_code == status_code
        assert response.json()['detail'] == detail


@mark.asyncio
class TestUpdateProfile:
    url_path = "api/users/"

    @mark.usefixtures('mock_rate_limit')
    async def test_was_successfully(self, client, access_token, user):
        body = {
            "username": "usernew",
            "first_name": "Степан",
            "last_name": "Гіга"
        }

        response = client.patch(
            self.url_path,
            json=body,
            headers={"Authorization": f"Bearer {access_token}"},
        )

        user.update(body)

        assert response.status_code == status.HTTP_200_OK
        assert response.json()['email'] == user['email']
        assert response.json()['first_name'] == body['first_name']
        assert response.json()['last_name'] == body['last_name']

    @mark.usefixtures('mock_rate_limit')
    @mark.parametrize(
        "status_code, detail, authorization",
        (
                (status.HTTP_401_UNAUTHORIZED, "Not authenticated", None),
                (status.HTTP_401_UNAUTHORIZED, "Could not validate credentials", "invalid"),
                (status.HTTP_400_BAD_REQUEST, "That username is already taken. Please try another one.", "valid"),
        )
    )
    async def test_exceptions(self, client, access_token, user,
                              status_code, detail, authorization):
        if authorization == "invalid":
            headers = {"Authorization": "Bearer invalid_access_token"}
        elif authorization == "valid":
            headers = {"Authorization": f"Bearer {access_token}"}
        else:
            headers = {}

        response = client.patch(
            self.url_path,
            json={"username": user['username'], "first_name": user['first_name'], "last_name": user['last_name']},
            headers=headers,
        )

        assert response.status_code == status_code
        assert response.json()['detail'] == detail


@mark.asyncio
class TestGetProfile:
    url_path = "api/users/{username}"

    @mark.usefixtures('mock_rate_limit')
    @mark.parametrize(
        "status_code, detail, authorization",
        (
                (status.HTTP_401_UNAUTHORIZED, "Not authenticated", None),
                (status.HTTP_401_UNAUTHORIZED, "Could not validate credentials", "invalid"),
                (status.HTTP_404_NOT_FOUND, "User not found", "valid"),
        )
    )
    async def test_exceptions(self, client, access_token, user,
                              status_code, detail, authorization):
        if authorization == "invalid":
            headers = {"Authorization": "Bearer invalid_access_token"}
        elif authorization == "valid":
            headers = {"Authorization": f"Bearer {access_token}"}
        else:
            headers = {}

        response = client.get(
            self.url_path.format(username="invalid_username"),
            headers=headers
        )

        assert response.status_code == status_code
        assert response.json()['detail'] == detail

    @mark.usefixtures('mock_rate_limit')
    async def test_was_successfully(self, client, access_token, user):
        response = client.get(
            self.url_path.format(username=user['username']),
            headers={"Authorization": f"Bearer {access_token}"}
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json()['username'] == user['username']
        assert isinstance(response.json()['number_of_images'], int)


@mark.asyncio
class TestBanUser:
    url_path = "api/users/ban/{user_id}"

    @mark.parametrize(
        "status_code, detail, authorization",
        (
                (status.HTTP_401_UNAUTHORIZED, "Not authenticated", None),
                (status.HTTP_401_UNAUTHORIZED, "Could not validate credentials", "invalid"),
                (status.HTTP_403_FORBIDDEN, "Access denied. Access open to \"moderator\"", "valid"),

        )
    )
    async def test_exceptions(self, client, access_token,
                              status_code, detail, authorization):
        if authorization == "invalid":
            headers = {"Authorization": "Bearer invalid_access_token"}
        elif authorization == "valid":
            headers = {"Authorization": f"Bearer {access_token}"}
        else:
            headers = {}

        response = client.post(
            self.url_path.format(user_id=2),
            headers=headers,
        )

        assert response.status_code == status_code
        assert response.json()['detail'] == detail

    async def test_was_successfully(self, client, access_token, user, session):
        current_user: User = await session.scalar(select(User).filter(User.email == user['email']))
        current_user.role = "admin"
        await session.commit()

        user_id = 2

        response = client.post(
            self.url_path.format(user_id=user_id),
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json()['id'] == user_id
        assert response.json()['is_active'] is False


@mark.asyncio
class TestUnbanUser:
    url_path = "api/users/unban/{user_id}"

    async def test_was_successfully(self, client, access_token, user):
        user_id = 2

        response = client.post(
            self.url_path.format(user_id=user_id),
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json()['id'] == user_id
        assert response.json()['is_active'] is True

    @mark.parametrize(
        "status_code, detail, authorization",
        (
                (status.HTTP_401_UNAUTHORIZED, "Not authenticated", None),
                (status.HTTP_401_UNAUTHORIZED, "Could not validate credentials", "invalid"),
                (status.HTTP_403_FORBIDDEN, "Access denied. Access open to \"moderator\"", "valid"),

        )
    )
    async def test_exceptions(self, client, access_token, session, user,
                              status_code, detail, authorization):
        if status_code == status.HTTP_403_FORBIDDEN:
            current_user: User = await session.scalar(select(User).filter(User.email == user['email']))
            current_user.role = "moderator"
            await session.commit()

        if authorization == "invalid":
            headers = {"Authorization": "Bearer invalid_access_token"}
        elif authorization == "valid":
            headers = {"Authorization": f"Bearer {access_token}"}
        else:
            headers = {}

        response = client.post(
            self.url_path.format(user_id=2),
            headers=headers,
        )

        assert response.status_code == status_code
        assert response.json()['detail'] == detail
