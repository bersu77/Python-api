from datetime import datetime
from app import db


post_tags = db.Table(
    "post_tags",
    db.Column("post_id", db.Integer, db.ForeignKey("posts.id"), primary_key=True),
    db.Column("category_id", db.Integer, db.ForeignKey("categories.id"), primary_key=True),
)

post_likes = db.Table(
    "post_likes",
    db.Column("user_id", db.Integer, db.ForeignKey("users.id"), primary_key=True),
    db.Column("post_id", db.Integer, db.ForeignKey("posts.id"), primary_key=True),
    db.Column("created_at", db.DateTime, default=datetime.utcnow),
)

post_bookmarks = db.Table(
    "post_bookmarks",
    db.Column("user_id", db.Integer, db.ForeignKey("users.id"), primary_key=True),
    db.Column("post_id", db.Integer, db.ForeignKey("posts.id"), primary_key=True),
    db.Column("created_at", db.DateTime, default=datetime.utcnow),
)


class Post(db.Model):
    __tablename__ = "posts"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(256), nullable=False)
    slug = db.Column(db.String(256), unique=True, nullable=False, index=True)
    content = db.Column(db.Text, nullable=False)
    excerpt = db.Column(db.String(512), nullable=True)
    cover_image = db.Column(db.String(512), nullable=True)
    status = db.Column(db.String(20), default="draft", index=True)
    view_count = db.Column(db.Integer, default=0)
    reading_time = db.Column(db.Integer, default=0)
    is_featured = db.Column(db.Boolean, default=False)
    is_pinned = db.Column(db.Boolean, default=False)
    published_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    author_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)

    comments = db.relationship("Comment", backref="post", lazy="dynamic", cascade="all, delete-orphan")
    categories = db.relationship("Category", secondary=post_tags, backref=db.backref("posts", lazy="dynamic"))
    liked_by = db.relationship("User", secondary=post_likes, backref=db.backref("liked_posts", lazy="dynamic"))
    bookmarked_by = db.relationship("User", secondary=post_bookmarks, backref=db.backref("bookmarked_posts", lazy="dynamic"))

    @staticmethod
    def generate_slug(title):
        import re
        slug = title.lower().strip()
        slug = re.sub(r"[^\w\s-]", "", slug)
        slug = re.sub(r"[-\s]+", "-", slug)
        slug = slug.strip("-")
        existing = Post.query.filter(Post.slug.like(f"{slug}%")).count()
        if existing:
            slug = f"{slug}-{existing + 1}"
        return slug

    @staticmethod
    def calculate_reading_time(content):
        words_per_minute = 200
        word_count = len(content.split())
        return max(1, round(word_count / words_per_minute))

    def publish(self):
        self.status = "published"
        self.published_at = datetime.utcnow()

    def unpublish(self):
        self.status = "draft"
        self.published_at = None

    def increment_views(self):
        self.view_count += 1
        db.session.commit()

    @property
    def likes_count(self):
        return len(self.liked_by)

    @property
    def comments_count(self):
        return self.comments.count()

    @property
    def bookmarks_count(self):
        return len(self.bookmarked_by)

    def is_liked_by(self, user):
        return user in self.liked_by

    def is_bookmarked_by(self, user):
        return user in self.bookmarked_by

    def to_dict(self, include_content=True):
        data = {
            "id": self.id,
            "title": self.title,
            "slug": self.slug,
            "excerpt": self.excerpt,
            "cover_image": self.cover_image,
            "status": self.status,
            "view_count": self.view_count,
            "reading_time": self.reading_time,
            "is_featured": self.is_featured,
            "is_pinned": self.is_pinned,
            "likes_count": self.likes_count,
            "comments_count": self.comments_count,
            "bookmarks_count": self.bookmarks_count,
            "author": self.author.to_dict(),
            "categories": [c.to_dict() for c in self.categories],
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
        if include_content:
            data["content"] = self.content
        return data

    def __repr__(self):
        return f"<Post {self.title[:50]}>"
