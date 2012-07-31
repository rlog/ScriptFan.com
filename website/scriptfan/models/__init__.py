#!/usr/bin/env python
#-*-coding:utf-8-*-
from flask.ext.sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

def getUserObject(slug=None, user_id=None):
    user = None
    if not slug and not user_id:
        if 'user' in session:
            user = g.user
    elif slug:
        user = User.query.filter_by(slug=slug).first()
    elif user_id:
        user = User.query.filter_by(id=user_id).first()
    return user

class UserInfo(db.Model):
    """
    用户信息表
    """
    __tablename__ = 'user_info'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    motoo = db.Column(db.String(255))
    introduction = db.Column(db.Text)
    phone = db.Column(db.String(15), unique=True, nullable=True) # 手机号码
    phone_status = db.Column(db.Integer, nullable=True) # 手机可见度: 0-不公开 1-公开 2-向成员公开
    photo = db.Column(db.String(255), nullable=True) # 存一张照片，既然有线下的聚会的，总得认得人才行

    def __init__(self, user_id):
        self.user_id = user_id

    def __repr__(self):
        return "<UserInfo (%s)>" % self.user_id

class User(db.Model):
    """
    用户表
    修改email地址时需要经过验证
    """
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(45), unique=True, nullable=False) # 登陆使用的
    email_status = db.Column(db.Integer, nullable=True) # 邮箱可见度: 0-不公开 1-公开 2-向成员公开
    nickname = db.Column(db.String(45), unique=True, nullable=False) # 昵称, 显示时用的
    password = db.Column(db.String(45), nullable=True) # 密码
    is_email_verified = db.Column(db.Boolean, nullable=False)
    slug = db.Column(db.String(45), nullable=True) # 用户页面
    created_time = db.Column(db.DateTime, nullable=False) # 用户注册时间
    modified_time = db.Column(db.DateTime, nullable=False) # 用户更新时间
    last_login_time = db.Column(db.DateTime) # 最后一次登陆时间
    privilege = db.Column(db.Integer, default=3) # 权重：3-普通用户 4-管理员
    info = db.relationship('UserInfo', uselist=False) # 用户附加信息
    
    # shared topics
    topics = db.relationship('Topic', backref='speaker', lazy='dynamic')

    def __init__(self, nickname, email):
        self.nickname = nickname
        self.email = email
        self.paste_num = 0
        self.created_time = self.modified_time = datetime.now()
        self.is_email_verified = True

    def __repr__(self):
        return "<User (%s|%s)>" % (self.nickname, self.email)

    def set_password(self, password):
        self.password = hashPassword(password)

    @property
    def url(self):
        if self.slug:
            return url_for('userapp.view', slug=self.slug)
        return url_for('userapp.view', user_id=self.id)

    def get_avatar_url(self, size=20):
        return "http://www.gravatar.com/avatar/%s?size=%s&d=%s/static/images/avatar/default.jpg" % (
                hashlib.md5(self.email).hexdigest(),
                size,
                request.url_root)

class UserOpenID(db.Model):
    """
    用户绑定OpenID的表
    一个用户可以对应多个OpenID
    """
    __tablename__ = 'user_openid'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False) # openid关联的用户
    openid_src = db.Column(db.String(45), nullable=False) # openid的提供商，比如 google 
    openid_url = db.Column(db.String(255), nullable=False, unique=True) # 记录的 openid, 不能重复

class Resource(db.Model):
    """
    资源表
    汇集图片、视频、演示文稿等资源, 用于嵌入活动中
    """
    __tablename__ = 'resources'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id')) # 发布者
    filetype = db.Column(db.String(45)) # 类型: video, audio, image, slides, pdf, webpage, ...
    created_time = db.Column(db.DateTime)
    modified_time = db.Column(db.DateTime)

# 活动相关资源
topic_resources = db.Table('topic_resources',
    db.Column('topic_id', db.Integer, db.ForeignKey('topics.id'), primary_key=True),
    db.Column('resource_id', db.Integer, db.ForeignKey('resources.id'), primary_key=True),
)

# 用户参与投票的跟踪表（活动关闭后可清除此表数据）
topic_users = db.Table('topic_users',
    db.Column('topic_id', db.Integer, db.ForeignKey('topics.id'), primary_key=True),
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
)

class Topic(db.Model):
    """
    活动的话题
    """
    __tablename__ = 'topics'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255)) # 话题名称
    intro = db.Column(db.Text) # 简要介绍
    rate_count = db.Column(db.Integer, default=0) # 投票数
    user = db.relationship(User, uselist=False)
    followers = db.relationship(User, secondary=topic_users) # 参与者
    resources = db.relationship(Resource, secondary=topic_resources) # 话题相关资源

# 用户参与活动的跟踪表
activity_users = db.Table('activity_users',
    db.Column('activity_id', db.Integer, db.ForeignKey('activities.id'), primary_key=True),
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
)

# 活动相关资源
activity_resources = db.Table('activity_resources',
    db.Column('activity_id', db.Integer, db.ForeignKey('activities.id'), primary_key=True),
    db.Column('resource_id', db.Integer, db.ForeignKey('resources.id'), primary_key=True),
)

class Activity(db.Model):
    """
    活动表
    每期活动需要一个公告
    """
    __tablename__ = 'activities'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id')) # 发起人
    title = db.Column(db.String(255)) # 活动标题
    content = db.Column(db.Text) # 活动介绍
    slug = db.Column(db.String(255)) # 页面地址
    start_time = db.Column(db.DateTime) # 活动开始时间
    end_time = db.Column(db.DateTime) # 活动结束时间
    address = db.Column(db.String(255)) # 活动地址
    longitude = db.Column(db.Numeric(10, 7)) # 经度
    Latitude = db.Column(db.Numeric(10, 7)) # 纬度
    created_time = db.Column(db.DateTime) # 活动创建时间
    modified_time = db.Column(db.DateTime) # 活动更新时间

    followers = db.relationship(User, secondary=activity_users) # 参与者
    resources = db.relationship(Resource, secondary=activity_resources) # 话题相关资源

class ActivityComment(db.Model):
    """
    活动评论表
    如果是未注册用户使用openid注册，则仅将openid记录在cookie中
    """
    __tablename__ = 'activity_comments'

    id = db.Column(db.Integer, primary_key=True)
    user = db.relationship(User, uselist=False) # 作者
    author_name = db.Column(db.String(50), nullable=False) # 作者昵称
    author_email = db.Column(db.String(255)) # 作者邮件地址
    author_site = db.Column(db.String(255)) # 作者网址
    content = db.Column(db.Text, nullable=False) # 评论内容
    created_time = db.Column(db.DateTime) # 创建日期
    modified_time = db.Column(db.DateTime) # 更新日期

    parent = db.relationship(Topic, uselist=False) # 回复评论的引用
