from typing import Optional

import pydash
from pythorhead import Lemmy
from pythorhead.types import FeatureType

from src.db.comments.comments_dao import CommentsDao, comments_dao
from src.db.daily_threads.daily_threads_dao import DailyThreadsDao, daily_threads_dao
from src.db.daily_threads.daily_threads_record import DailyThreadsRecord
from src.db.game_day_threads.game_day_threads_dao import GameDayThreadsDao, game_day_threads_dao
from src.utils import logger
from src.utils.environment_util import environment_util

TAG = 'LemmyClient'

DICT_KEY_POST_VIEW = 'post_view'
DICT_KEY_POST = 'post'
DICT_KEY_ID = 'id'

REQUEST_TIMEOUT = 10


class LemmyClient:
    def __init__(self, lemmy_instance: str, bot_name: str, password: str, community_name: str,
                 client_game_day_threads_dao: Optional[GameDayThreadsDao] = None,
                 client_daily_threads_dao: Optional[DailyThreadsDao] = None,
                 client_comments_dao: Optional[CommentsDao] = None):
        self.lemmy_instance = lemmy_instance
        self.bot_name = bot_name
        self.password = password
        self.community_name = community_name
        self.client_game_day_threads_dao = client_game_day_threads_dao if client_game_day_threads_dao else game_day_threads_dao
        self.client_daily_threads_dao = client_daily_threads_dao if client_daily_threads_dao else daily_threads_dao
        self.client_comments_dao = client_comments_dao if client_comments_dao else comments_dao

        self.lemmy = Lemmy(self.lemmy_instance, request_timeout=REQUEST_TIMEOUT)
        self.lemmy.log_in(self.bot_name, self.password)
        self.community_id = self.lemmy.discover_community(self.community_name)
        if self.community_id is None:
            logger.e(TAG, f"__init__(): Community {community_name} not found")
            raise ValueError(f"Community {community_name} not found")

    def create_game_day_thread(self, title, body, game_id) -> int:
        # TODO: update to return GDT record instead of post id
        post_id = pydash.get(self.lemmy.post.create(self.community_id, name=title, body=body),
                             f"{DICT_KEY_POST_VIEW}.{DICT_KEY_POST}.{DICT_KEY_ID}", -1)
        if post_id == -1:
            logger.e(TAG, f"create_game_day_thread(): Failed to create post for game {game_id}")
            return -1
        return self.client_game_day_threads_dao.insert_game_day_thread(post_id, game_id)

    def update_game_day_thread(self, title, body, post_id):
        self.lemmy.post.edit(post_id=post_id, name=title, body=body)

    def create_daily_thread(self, date, title, body) -> Optional[DailyThreadsRecord]:
        post_id = pydash.get(self.lemmy.post.create(self.community_id, name=title, body=body),
                             f"{DICT_KEY_POST_VIEW}.{DICT_KEY_POST}.{DICT_KEY_ID}", -1)
        if post_id == -1:
            logger.e(TAG, f"create_daily_thread(): Failed to create daily thread for date: {date}")
            return None
        return self.client_daily_threads_dao.insert_daily_thread(post_id, date, False)

    def update_daily_thread(self, post_id, title, body):
        self.lemmy.post.edit(post_id=post_id, name=title, body=body)

    def create_comment(self, post_id, game_id, content) -> int:
        # TODO: update to return comment record instead of comment id
        comment_id = pydash.get(self.lemmy.comment.create(post_id=post_id, content=content), f"comment_view.comment.id", -1)
        if comment_id == -1:
            logger.e(TAG, f"create_comment(): Failed to create comment. post_id: {post_id}; game_id: {game_id}")
            return -1
        return self.client_comments_dao.insert_comment(comment_id, game_id)

    def update_comment(self, comment_id, content):
        self.lemmy.comment.edit(comment_id=comment_id, content=content)

    def feature_daily_thread(self, post_id):
        self.lemmy.post.feature(post_id, True, FeatureType.Community)
        self.client_daily_threads_dao.feature_daily_thread(post_id)

    def unfeature_daily_thread(self, post_id):
        self.lemmy.post.feature(post_id, False, FeatureType.Community)
        self.client_daily_threads_dao.unfeature_daily_thread(post_id)


lemmy_client = LemmyClient(environment_util.lemmy_instance, environment_util.bot_name, environment_util.password,
                           environment_util.community_name)
