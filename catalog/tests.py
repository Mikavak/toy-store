from datetime import timedelta
from decimal import Decimal

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Category, Product
from .management.commands.seed_store import SEED_CATEGORIES, SEED_PRODUCTS


class CategoryTests(TestCase):
    def test_create_category(self):
        category = Category.objects.create(name="Конструкторы", slug="builders")
        category.full_clean()
        category.refresh_from_db()
        self.assertEqual(category.name, "Конструкторы")
        self.assertEqual(category.slug, "builders")
        self.assertEqual(str(category), "Конструкторы")

    def test_slug_is_unique(self):
        Category.objects.create(name="Конструкторы", slug="builders")
        with self.assertRaises(IntegrityError), transaction.atomic():
            Category.objects.create(name="Другие игрушки", slug="builders")

    def test_slug_is_required_and_not_generated(self):
        category = Category(name="Конструкторы")
        self.assertEqual(category.slug, "")
        with self.assertRaises(ValidationError) as error:
            category.full_clean()
        self.assertIn("slug", error.exception.message_dict)


class ProductTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.category = Category.objects.create(name="Конструкторы", slug="builders")

    def make_product(self, **overrides):
        fields = {
            "name": "Домик",
            "slug": "toy-house",
            "description": "Деревянный конструктор",
            "price": Decimal("1299.90"),
            "category": self.category,
            "recommended_age": "От 3 лет",
        }
        fields.update(overrides)
        return Product(**fields)

    def test_create_product(self):
        product = self.make_product(image="https://example.com/toy.jpg")
        product.full_clean()
        product.save()
        product.refresh_from_db()
        self.assertEqual(product.name, "Домик")
        self.assertEqual(product.slug, "toy-house")
        self.assertEqual(product.description, "Деревянный конструктор")
        self.assertEqual(product.price, Decimal("1299.90"))
        self.assertEqual(product.category, self.category)
        self.assertEqual(product.recommended_age, "От 3 лет")
        self.assertEqual(product.image, "https://example.com/toy.jpg")
        self.assertEqual(str(product), "Домик")
        self.assertQuerySetEqual(self.category.products.all(), [product])

    def test_defaults_and_optional_image(self):
        product = self.make_product()
        product.full_clean()
        product.save()
        product.refresh_from_db()
        self.assertTrue(product.is_available)
        self.assertEqual(product.image, "")

    def test_unavailable_product_can_be_saved(self):
        product = self.make_product(is_available=False)
        product.save()
        product.refresh_from_db()
        self.assertFalse(product.is_available)

    def test_slug_is_unique(self):
        self.make_product().save()
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.make_product(name="Другой домик").save()

    def test_slug_is_required_and_not_generated(self):
        product = self.make_product(slug="")
        with self.assertRaises(ValidationError) as error:
            product.full_clean()
        self.assertIn("slug", error.exception.message_dict)
        self.assertEqual(product.slug, "")

    def test_category_is_required(self):
        product = self.make_product(category=None)
        with self.assertRaises(ValidationError) as error:
            product.full_clean()
        self.assertIn("category", error.exception.message_dict)
        with self.assertRaises(IntegrityError), transaction.atomic():
            product.save()

    def test_category_with_product_cannot_be_deleted(self):
        product = self.make_product()
        product.save()
        with self.assertRaises(ProtectedError):
            self.category.delete()
        self.assertTrue(Category.objects.filter(pk=self.category.pk).exists())
        self.assertTrue(Product.objects.filter(pk=product.pk).exists())

    def test_negative_price_fails_validation(self):
        product = self.make_product(price=Decimal("-0.01"))
        with self.assertRaises(ValidationError) as error:
            product.full_clean(validate_constraints=False)
        self.assertIn("price", error.exception.message_dict)

    def test_database_rejects_negative_price(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.make_product(price=Decimal("-0.01")).save()

    def test_database_rejects_update_to_negative_price(self):
        product = self.make_product()
        product.save()
        with self.assertRaises(IntegrityError), transaction.atomic():
            Product.objects.filter(pk=product.pk).update(price=Decimal("-0.01"))
        product.refresh_from_db()
        self.assertEqual(product.price, Decimal("1299.90"))

    def test_valid_price_boundaries(self):
        for index, price in enumerate((Decimal("0.00"), Decimal("99999999.99"))):
            with self.subTest(price=price):
                product = self.make_product(slug=f"boundary-{index}", price=price)
                product.full_clean()
                product.save()
                product.refresh_from_db()
                self.assertEqual(product.price, price)

    def test_invalid_price_precision(self):
        for price in (Decimal("100000000.00"), Decimal("1.001")):
            with self.subTest(price=price):
                with self.assertRaises(ValidationError) as error:
                    self.make_product(price=price).full_clean()
                self.assertIn("price", error.exception.message_dict)

    def test_timestamps(self):
        before = timezone.now()
        product = self.make_product()
        product.save()
        product.refresh_from_db()
        after = timezone.now()
        self.assertLessEqual(before, product.created_at)
        self.assertLessEqual(product.created_at, after)
        self.assertLessEqual(before, product.updated_at)
        self.assertLessEqual(product.updated_at, after)
        created_at = product.created_at
        earlier = before - timedelta(days=1)
        Product.objects.filter(pk=product.pk).update(updated_at=earlier)
        product.refresh_from_db()
        product.name = "Новый домик"
        product.save()
        product.refresh_from_db()
        self.assertEqual(product.created_at, created_at)
        self.assertGreater(product.updated_at, earlier)


class CatalogAdminTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin_user = get_user_model().objects.create_superuser(
            username="admin", email="admin@example.com", password="test-password"
        )
        cls.builders = Category.objects.create(
            name="Конструкторы", slug="builders"
        )
        cls.soft_toys = Category.objects.create(
            name="Мягкие игрушки", slug="soft-toys"
        )
        cls.available_product = Product.objects.create(
            name="Деревянный домик",
            slug="wooden-house",
            description="Набор деталей для сборки домика.",
            price=Decimal("1299.90"),
            category=cls.builders,
            recommended_age="От 3 лет",
        )
        cls.unavailable_product = Product.objects.create(
            name="Плюшевый медведь",
            slug="plush-bear",
            description="Мягкая игрушка для сна.",
            price=Decimal("899.00"),
            category=cls.soft_toys,
            recommended_age="От 1 года",
            is_available=False,
        )

    def setUp(self):
        self.category_changelist_url = reverse("admin:catalog_category_changelist")
        self.product_changelist_url = reverse("admin:catalog_product_changelist")

    def test_models_are_registered(self):
        self.assertIn(Category, admin.site._registry)
        self.assertIn(Product, admin.site._registry)

    def test_unauthenticated_user_is_redirected_to_login(self):
        for url in (self.category_changelist_url, self.product_changelist_url):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertRedirects(
                    response,
                    f"{reverse('admin:login')}?next={url}",
                )

    def test_admin_can_view_category_changelist_with_data(self):
        self.client.force_login(self.admin_user)

        response = self.client.get(self.category_changelist_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.builders.name)
        self.assertContains(response, self.builders.slug)
        self.assertContains(response, self.soft_toys.name)

    def test_admin_can_search_categories_by_name(self):
        self.client.force_login(self.admin_user)

        response = self.client.get(self.category_changelist_url, {"q": "Конструкт"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.builders.name)
        self.assertNotContains(response, self.soft_toys.name)

    def test_admin_can_view_product_changelist_with_data(self):
        self.client.force_login(self.admin_user)

        response = self.client.get(self.product_changelist_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.available_product.name)
        self.assertContains(response, self.builders.name)
        self.assertContains(response, self.available_product.price)
        self.assertContains(response, self.available_product.recommended_age)

    def test_admin_can_search_products_by_name_description_and_slug(self):
        self.client.force_login(self.admin_user)

        for query in ("Деревянный", "деталей", "wooden-house"):
            with self.subTest(query=query):
                response = self.client.get(self.product_changelist_url, {"q": query})
                self.assertContains(response, self.available_product.name)
                self.assertNotContains(response, self.unavailable_product.name)

    def test_admin_can_filter_products_by_category_and_availability(self):
        self.client.force_login(self.admin_user)

        response = self.client.get(
            self.product_changelist_url,
            {
                "category__id__exact": self.soft_toys.pk,
                "is_available__exact": "0",
            },
        )

        self.assertContains(response, self.unavailable_product.name)
        self.assertNotContains(response, self.available_product.name)

    def test_admin_can_create_product(self):
        self.client.force_login(self.admin_user)

        response = self.client.post(
            reverse("admin:catalog_product_add"),
            {
                "name": "Набор кубиков",
                "slug": "building-blocks",
                "description": "Яркие кубики для первых построек.",
                "price": "749.50",
                "category": self.builders.pk,
                "recommended_age": "От 2 лет",
                "image": "",
                "is_available": "on",
                "_save": "Save",
            },
        )

        self.assertEqual(response.status_code, 302)
        product = Product.objects.get(slug="building-blocks")
        self.assertEqual(product.price, Decimal("749.50"))
        self.assertEqual(product.category, self.builders)
        self.assertTrue(product.is_available)

    def test_admin_can_change_product_price_category_and_availability(self):
        self.client.force_login(self.admin_user)

        response = self.client.post(
            reverse("admin:catalog_product_change", args=[self.available_product.pk]),
            {
                "name": self.available_product.name,
                "slug": self.available_product.slug,
                "description": self.available_product.description,
                "price": "1499.00",
                "category": self.soft_toys.pk,
                "recommended_age": self.available_product.recommended_age,
                "image": "",
                "_save": "Save",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.available_product.refresh_from_db()
        self.assertEqual(self.available_product.price, Decimal("1499.00"))
        self.assertEqual(self.available_product.category, self.soft_toys)
        self.assertFalse(self.available_product.is_available)

    def test_admin_does_not_delete_category_with_products(self):
        self.client.force_login(self.admin_user)
        delete_url = reverse("admin:catalog_category_delete", args=[self.builders.pk])

        response = self.client.post(delete_url, {"post": "yes"})

        self.assertEqual(response.status_code, 200)
        self.assertTrue(Category.objects.filter(pk=self.builders.pk).exists())


class SeedStoreCommandTests(TestCase):
    def test_seed_store_creates_categories_and_products(self):
        call_command("seed_store")

        category_slugs = [category["slug"] for category in SEED_CATEGORIES]
        product_slugs = [product["slug"] for product in SEED_PRODUCTS]
        self.assertEqual(
            Category.objects.filter(slug__in=category_slugs).count(),
            len(SEED_CATEGORIES),
        )
        self.assertEqual(
            Product.objects.filter(slug__in=product_slugs).count(),
            len(SEED_PRODUCTS),
        )

    def test_seed_store_assigns_products_to_categories_with_valid_prices(self):
        call_command("seed_store")

        seeded_products = Product.objects.filter(
            slug__in=[product["slug"] for product in SEED_PRODUCTS]
        ).select_related("category")
        self.assertEqual(seeded_products.count(), len(SEED_PRODUCTS))
        self.assertEqual(
            {product.category.slug for product in seeded_products},
            {category["slug"] for category in SEED_CATEGORIES},
        )
        products_by_slug = {product.slug: product for product in seeded_products}
        for expected_product in SEED_PRODUCTS:
            with self.subTest(product=expected_product["slug"]):
                product = products_by_slug[expected_product["slug"]]
                self.assertEqual(product.price, expected_product["price"])
                self.assertEqual(
                    product.category.slug, expected_product["category_slug"]
                )
        for category in SEED_CATEGORIES:
            with self.subTest(category=category["slug"]):
                self.assertEqual(
                    seeded_products.filter(category__slug=category["slug"]).count(), 3
                )

    def test_seed_store_is_idempotent(self):
        call_command("seed_store")
        category_count = Category.objects.count()
        product_count = Product.objects.count()

        call_command("seed_store")

        self.assertEqual(Category.objects.count(), category_count)
        self.assertEqual(Product.objects.count(), product_count)

    def test_seed_store_preserves_existing_user_products(self):
        user_category = Category.objects.create(
            name="Пользовательская категория", slug="user-category"
        )
        user_product = Product.objects.create(
            name="Пользовательский товар",
            slug="user-product",
            description="Товар, созданный до запуска команды.",
            price=Decimal("123.45"),
            category=user_category,
            recommended_age="От 7 лет",
            is_available=False,
        )

        call_command("seed_store")

        user_product.refresh_from_db()
        self.assertEqual(user_product.category, user_category)
        self.assertEqual(user_product.price, Decimal("123.45"))
        self.assertFalse(user_product.is_available)
