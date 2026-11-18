from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.test import TestCase
from django.utils import timezone

from .models import Category, Product


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
