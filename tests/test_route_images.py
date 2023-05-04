from pytest import mark, fixture

from fastapi import status
from sqlalchemy import select

from app.database.models import Image, UserRole, User


@fixture(scope='module')
def new_user(client) -> dict:
    user = {
        "email": "email.new@test.com",
        "username": "username_new",
        "password": "test_pwd",
        "first_name": "Stepan",
        "last_name": "Giga",
    }

    res = client.post('/api/auth/signup', json=user)
    user['id'] = res.json()['user']['id']

    return user


@fixture(scope='session')
def image() -> dict:
    return {
        "url": "https://res.cloudinary.com/dlwnuqx3p/image/upload/cld-sample-5",
        "public_id": "cld-sample-5",
        "version": "1678785308",
        "description": "Image description",
        "tags": ["tag1", "tag2", "tag3", "tag4", "tag5"],
    }


@mark.asyncio
class TestUploadImage:
    url_path = "api/images/"

    @mark.usefixtures('mock_rate_limit')
    @mark.parametrize(
        "status_code, detail, authorization, type_",
        (
                (status.HTTP_401_UNAUTHORIZED, "Not authenticated", None, None),
                (status.HTTP_401_UNAUTHORIZED, "Could not validate credentials", "invalid", None),
                (status.HTTP_422_UNPROCESSABLE_ENTITY, "Maximum five tags can be added", "valid", "invalid_count_tags"),
                (status.HTTP_422_UNPROCESSABLE_ENTITY, "Invalid length tag: ta", "valid", "invalid_length_tag"),
                (status.HTTP_422_UNPROCESSABLE_ENTITY, "Invalid image file", "valid", None),
        )
    )
    async def test_exceptions(self, client, access_token, image, mocker,
                              status_code, detail, authorization, type_):
        mocker.patch("app.services.cloudinary.upload_image", return_value=None)

        if authorization == "invalid":
            headers = {"Authorization": "Bearer invalid_access_token"}
        elif authorization == "valid":
            headers = {"Authorization": f"Bearer {access_token}"}
        else:
            headers = {}

        data = {
            "description": image['description'],
            "tags": image['tags'].copy()
        }

        if type_ == "invalid_count_tags":
            data['tags'] += 'tag6'
        elif type_ == "invalid_length_tag":
            data['tags'] = ['ta']

        response = client.post(
            self.url_path,
            headers=headers,
            files={"file": ("test.png", b"image", "image/png")},
            data=data
        )

        assert response.status_code == status_code
        assert response.json()['detail'] == detail

    @mark.usefixtures('mock_rate_limit')
    async def test_was_successfully(self, client, access_token, image, mocker):
        mock_image = {
            "url": image['url'],
            "public_id": image['public_id'],
            "version": image['version']
        }
        mocker.patch("app.services.cloudinary.upload_image", return_value=mock_image)

        response = client.post(
            self.url_path,
            headers={"Authorization": f"Bearer {access_token}"},
            files={"file": ("test.png", b"image", "image/png")},
            data={"description": image['description'], "tags": image['tags']}
        )

        image['id'] = response.json()['image']['id']

        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()['message'] == "Image successfully uploaded"
        assert response.json()['image']['url'] == mock_image['url']


@mark.asyncio
class TestGetImages:
    url_path = "api/images/"

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
    async def test_was_successfully(self, client, access_token, image):
        response = client.get(
            self.url_path,
            params={'tags': image['tags'][0]},
            headers={"Authorization": f"Bearer {access_token}"}
        )

        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.json(), list)
        assert len(response.json()) == 1


@mark.asyncio
class TestGetImageById:
    url_path = "api/images/{image_id}"

    @mark.parametrize(
        "status_code, detail, authorization",
        (
                (status.HTTP_401_UNAUTHORIZED, "Not authenticated", None),
                (status.HTTP_401_UNAUTHORIZED, "Could not validate credentials", "invalid"),
                (status.HTTP_404_NOT_FOUND, "Not found image", "valid"),
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

        response = client.get(
            self.url_path.format(image_id=0),
            headers=headers
        )

        assert response.status_code == status_code
        assert response.json()['detail'] == detail

    async def test_was_successfully(self, client, access_token, image):
        response = client.get(
            self.url_path.format(image_id=image['id']),
            headers={"Authorization": f"Bearer {access_token}"}
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json()['id'] == image['id']
        assert response.json()['url'] == image['url']
        assert response.json()['description'] == image['description']


@mark.asyncio
class TestUpdateImageData:
    url_path = "api/images/"

    @mark.usefixtures('mock_rate_limit')
    @mark.parametrize(
        "status_code, detail, authorization",
        (
                (status.HTTP_401_UNAUTHORIZED, "Not authenticated", None),
                (status.HTTP_401_UNAUTHORIZED, "Could not validate credentials", "invalid"),
                (status.HTTP_422_UNPROCESSABLE_ENTITY, "Maximum five tags can be added", "valid"),
                (status.HTTP_404_NOT_FOUND, "Not found image", "valid"),
                (status.HTTP_403_FORBIDDEN, "Access denied", "valid"),
        )
    )
    async def test_exceptions(self, client, access_token, image, session, user, new_user,
                              status_code, detail, authorization):
        if authorization == "invalid":
            headers = {"Authorization": "Bearer invalid_access_token"}
        elif authorization == "valid":
            headers = {"Authorization": f"Bearer {access_token}"}
        else:
            headers = {}

        body = {
            "image_id": image['id'],
            "description": "New image description",
            "tags": image['tags'].copy()
        }

        if status_code == status.HTTP_422_UNPROCESSABLE_ENTITY:
            body['tags'].append('tag6')
        elif status_code == status.HTTP_404_NOT_FOUND:
            body['image_id'] = 10
        elif status_code == status.HTTP_403_FORBIDDEN:
            db_image = await session.scalar(select(Image).filter(Image.id == body['image_id']))
            db_image.user_id = new_user['id']
            await session.commit()

            current_user = await session.scalar(select(User).filter(User.id == user['id']))
            current_user.role = UserRole.moderator
            await session.commit()

        response = client.patch(
            self.url_path,
            headers=headers,
            json=body
        )

        assert response.status_code == status_code
        assert response.json()['detail'] == detail

    @mark.usefixtures('mock_rate_limit')
    async def test_was_successfully(self, client, access_token, image, session, user):
        current_user = await session.scalar(select(User).filter(User.id == user['id']))
        current_user.role = UserRole.admin
        await session.commit()

        body = {
            "image_id": image['id'],
            "description": "New image description",
            "tags": image['tags'][1:4]
        }

        response = client.patch(
            self.url_path,
            headers={"Authorization": f"Bearer {access_token}"},
            json=body
        )

        image.update(body)

        assert response.status_code == status.HTTP_200_OK
        assert response.json()['id'] == image['id']
        assert response.json()['url'] == image['url']
        assert response.json()['description'] == image['description']


@mark.asyncio
class TestImageDelete:
    url_path = "api/images/{image_id}"

    @mark.usefixtures('mock_rate_limit')
    @mark.parametrize(
        "status_code, detail, authorization",
        (
                (status.HTTP_401_UNAUTHORIZED, "Not authenticated", None),
                (status.HTTP_401_UNAUTHORIZED, "Could not validate credentials", "invalid"),
                (status.HTTP_404_NOT_FOUND, "Not found image", "valid"),
                (status.HTTP_403_FORBIDDEN, "Access denied", "valid"),
        )
    )
    async def test_exceptions(self, client, access_token, image, session, user, new_user,
                              status_code, detail, authorization):
        if authorization == "invalid":
            headers = {"Authorization": "Bearer invalid_access_token"}
        elif authorization == "valid":
            headers = {"Authorization": f"Bearer {access_token}"}
        else:
            headers = {}

        image_id = image['id']

        if status_code == status.HTTP_404_NOT_FOUND:
            image_id = 10
        elif status_code == status.HTTP_403_FORBIDDEN:
            db_image = await session.scalar(select(Image).filter(Image.id == image_id))
            db_image.user_id = new_user['id']
            await session.commit()

            current_user = await session.scalar(select(User).filter(User.id == user['id']))
            current_user.role = UserRole.moderator
            await session.commit()

        response = client.delete(
            self.url_path.format(image_id=image_id),
            headers=headers,
        )

        assert response.status_code == status_code
        assert response.json()['detail'] == detail

    @mark.usefixtures('mock_rate_limit')
    async def test_was_successfully(self, client, access_token, image, session, user):
        current_user = await session.scalar(select(User).filter(User.id == user['id']))
        current_user.role = UserRole.admin
        await session.commit()

        response = client.delete(
            self.url_path.format(image_id=image['id']),
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json()['message'] == 'Image successfully deleted'


