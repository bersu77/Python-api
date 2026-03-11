import random
from faker import Faker
from app import db
from app.models.user import User
from app.models.post import Post
from app.models.category import Category
from app.models.comment import Comment

fake = Faker()


def seed_categories():
    categories_data = [
        {"name": "Technology", "description": "Tech news and tutorials", "color": "#3b82f6", "icon": "laptop"},
        {"name": "Programming", "description": "Code and development", "color": "#10b981", "icon": "code"},
        {"name": "Design", "description": "UI/UX and graphic design", "color": "#f59e0b", "icon": "palette"},
        {"name": "DevOps", "description": "Infrastructure and deployment", "color": "#ef4444", "icon": "server"},
        {"name": "Data Science", "description": "ML and data analysis", "color": "#8b5cf6", "icon": "chart"},
        {"name": "Mobile", "description": "Mobile development", "color": "#ec4899", "icon": "smartphone"},
        {"name": "Web Dev", "description": "Web development", "color": "#06b6d4", "icon": "globe"},
        {"name": "Security", "description": "Cybersecurity topics", "color": "#f97316", "icon": "shield"},
    ]

    for cat_data in categories_data:
        if not Category.query.filter_by(name=cat_data["name"]).first():
            category = Category(
                name=cat_data["name"],
                slug=Category.generate_slug(cat_data["name"]),
                description=cat_data["description"],
                color=cat_data["color"],
                icon=cat_data["icon"],
            )
            db.session.add(category)

    db.session.commit()
    print(f"Seeded {len(categories_data)} categories")


def seed_users(count=20):
    users = []
    for _ in range(count):
        username = fake.unique.user_name()[:64]
        user = User(
            username=username,
            email=fake.unique.email(),
            first_name=fake.first_name(),
            last_name=fake.last_name(),
            bio=fake.sentence(nb_words=12),
            location=fake.city(),
            is_active=True,
            is_verified=random.choice([True, False]),
        )
        user.set_password("password123")
        db.session.add(user)
        users.append(user)

    db.session.commit()
    print(f"Seeded {count} users")
    return users


def seed_posts(users, count=50):
    categories = Category.query.all()
    posts = []

    for _ in range(count):
        author = random.choice(users)
        title = fake.sentence(nb_words=random.randint(4, 10)).rstrip(".")
        content = "\n\n".join(fake.paragraphs(nb=random.randint(3, 8)))

        post = Post(
            title=title,
            slug=Post.generate_slug(title),
            content=content,
            excerpt=content[:200],
            reading_time=Post.calculate_reading_time(content),
            author_id=author.id,
            status="published",
            view_count=random.randint(0, 500),
            is_featured=random.random() < 0.1,
        )
        post.publish()

        num_categories = random.randint(1, 3)
        post.categories = random.sample(categories, min(num_categories, len(categories)))

        num_likes = random.randint(0, min(10, len(users)))
        post.liked_by = random.sample(users, num_likes)

        db.session.add(post)
        posts.append(post)

    db.session.commit()
    print(f"Seeded {count} posts")
    return posts


def seed_comments(users, posts, count=100):
    for _ in range(count):
        author = random.choice(users)
        post = random.choice(posts)

        comment = Comment(
            content=fake.paragraph(nb_sentences=random.randint(1, 4)),
            author_id=author.id,
            post_id=post.id,
        )
        db.session.add(comment)

    db.session.commit()
    print(f"Seeded {count} comments")


def seed_follows(users):
    for user in users:
        num_follows = random.randint(0, min(5, len(users) - 1))
        potential = [u for u in users if u.id != user.id]
        to_follow = random.sample(potential, num_follows)

        for target in to_follow:
            user.follow(target)

    db.session.commit()
    print(f"Seeded follow relationships")


def seed_all():
    print("Starting database seeding...")
    seed_categories()
    users = seed_users(20)
    posts = seed_posts(users, 50)
    seed_comments(users, posts, 100)
    seed_follows(users)
    print("Database seeding complete!")
