from decimal import Decimal

from django.core.management.base import BaseCommand

from catalog.models import Category, Product


SEED_CATEGORIES = (
    {"name": "Конструкторы", "slug": "seed-constructors"},
    {"name": "Мягкие игрушки", "slug": "seed-soft-toys"},
    {"name": "Машинки", "slug": "seed-toy-cars"},
    {"name": "Куклы", "slug": "seed-dolls"},
    {"name": "Развивающие игрушки", "slug": "seed-educational-toys"},
)

SEED_PRODUCTS = (
    {
        "name": "Деревянный городок",
        "slug": "seed-wooden-town-constructor",
        "description": "Набор деревянных деталей для строительства небольшого городка.",
        "price": Decimal("1490.00"),
        "category_slug": "seed-constructors",
        "recommended_age": "От 3 лет",
        "is_available": True,
    },
    {
        "name": "Космическая станция",
        "slug": "seed-space-station-constructor",
        "description": "Конструктор с яркими деталями для сборки космической станции.",
        "price": Decimal("2190.00"),
        "category_slug": "seed-constructors",
        "recommended_age": "От 5 лет",
        "is_available": True,
    },
    {
        "name": "Механическая мастерская",
        "slug": "seed-mechanics-workshop-constructor",
        "description": "Набор с шестерёнками и креплениями для первых механизмов.",
        "price": Decimal("1790.00"),
        "category_slug": "seed-constructors",
        "recommended_age": "От 6 лет",
        "is_available": True,
    },
    {
        "name": "Медвежонок Топа",
        "slug": "seed-topa-teddy-bear",
        "description": "Мягкий медвежонок с приятной на ощупь шерсткой.",
        "price": Decimal("990.00"),
        "category_slug": "seed-soft-toys",
        "recommended_age": "От 1 года",
        "is_available": True,
    },
    {
        "name": "Лисёнок Рыжик",
        "slug": "seed-ryzhik-fox",
        "description": "Компактная мягкая игрушка для игр дома и в дороге.",
        "price": Decimal("790.00"),
        "category_slug": "seed-soft-toys",
        "recommended_age": "От 1 года",
        "is_available": True,
    },
    {
        "name": "Сонный кит",
        "slug": "seed-sleepy-whale",
        "description": "Большой плюшевый кит с вышитыми деталями мордочки.",
        "price": Decimal("1390.00"),
        "category_slug": "seed-soft-toys",
        "recommended_age": "От 3 лет",
        "is_available": False,
    },
    {
        "name": "Городской электромобиль",
        "slug": "seed-city-electric-car",
        "description": "Инерционная машинка с открывающимися дверцами.",
        "price": Decimal("650.00"),
        "category_slug": "seed-toy-cars",
        "recommended_age": "От 3 лет",
        "is_available": True,
    },
    {
        "name": "Пожарная команда",
        "slug": "seed-fire-rescue-truck",
        "description": "Игровая пожарная машина с выдвижной лестницей.",
        "price": Decimal("1150.00"),
        "category_slug": "seed-toy-cars",
        "recommended_age": "От 4 лет",
        "is_available": True,
    },
    {
        "name": "Гоночный болид",
        "slug": "seed-racing-car",
        "description": "Легкая машинка с инерционным механизмом для быстрых заездов.",
        "price": Decimal("540.00"),
        "category_slug": "seed-toy-cars",
        "recommended_age": "От 3 лет",
        "is_available": True,
    },
    {
        "name": "Кукла Мила",
        "slug": "seed-doll-mila",
        "description": "Кукла в повседневном наряде с расчёской для волос.",
        "price": Decimal("1290.00"),
        "category_slug": "seed-dolls",
        "recommended_age": "От 3 лет",
        "is_available": True,
    },
    {
        "name": "Кукла-путешественница Ася",
        "slug": "seed-traveler-doll-asya",
        "description": "Кукла с рюкзаком и набором аксессуаров для игры в путешествие.",
        "price": Decimal("1590.00"),
        "category_slug": "seed-dolls",
        "recommended_age": "От 4 лет",
        "is_available": True,
    },
    {
        "name": "Кукла Лада с коляской",
        "slug": "seed-doll-lada-stroller",
        "description": "Кукла с лёгкой прогулочной коляской и пледом.",
        "price": Decimal("1890.00"),
        "category_slug": "seed-dolls",
        "recommended_age": "От 3 лет",
        "is_available": False,
    },
    {
        "name": "Сортер Геометрия",
        "slug": "seed-geometry-sorter",
        "description": "Деревянный сортер с фигурками основных геометрических форм.",
        "price": Decimal("850.00"),
        "category_slug": "seed-educational-toys",
        "recommended_age": "От 2 лет",
        "is_available": True,
    },
    {
        "name": "Магнитная азбука",
        "slug": "seed-magnetic-alphabet",
        "description": "Набор цветных магнитных букв для первых слов и игр.",
        "price": Decimal("720.00"),
        "category_slug": "seed-educational-toys",
        "recommended_age": "От 4 лет",
        "is_available": True,
    },
    {
        "name": "Лабиринт с бусинами",
        "slug": "seed-bead-maze",
        "description": "Компактный проволочный лабиринт для развития мелкой моторики.",
        "price": Decimal("680.00"),
        "category_slug": "seed-educational-toys",
        "recommended_age": "От 2 лет",
        "is_available": True,
    },
)


class Command(BaseCommand):
    help = "Creates demonstration categories and products for Toy Store."

    def handle(self, *args, **options):
        categories = {}
        created_categories = 0
        created_products = 0

        for category_data in SEED_CATEGORIES:
            category, created = Category.objects.get_or_create(
                slug=category_data["slug"],
                defaults={"name": category_data["name"]},
            )
            categories[category.slug] = category
            created_categories += created

        for product_data in SEED_PRODUCTS:
            product_data = product_data.copy()
            category = categories[product_data.pop("category_slug")]
            _, created = Product.objects.get_or_create(
                slug=product_data.pop("slug"),
                defaults={"category": category, **product_data},
            )
            created_products += created

        self.stdout.write(
            self.style.SUCCESS(
                "Seed data ready: "
                f"{created_categories} categories and {created_products} products created."
            )
        )
