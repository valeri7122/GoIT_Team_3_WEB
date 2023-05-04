from typing import Optional

from libgravatar import Gravatar


async def get_gravatar(email: str) -> Optional[str]:
    try:
        return Gravatar(email).get_image()
    except Exception as e:
        print(e)
