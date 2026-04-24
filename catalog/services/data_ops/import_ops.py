"""
catalog/services/data_ops/import_ops.py

Service for importing catalog data from CSV.
Supports UPSERT (Update or Insert) logic based on Slug/Handle and SKU.
"""

import csv
import io
from decimal import Decimal
from django.db import transaction
from django.utils.text import slugify

from catalog.models import Product, ProductVariant, Category
from catalog.services.product import product_create, variant_create

def import_products_from_csv(shop_id: str, user_id, csv_file_content: str):
    """
    Parses a CSV and synchronizes the catalog.
    """
    f = io.StringIO(csv_file_content)
    reader = csv.DictReader(f)
    
    stats = {"created": 0, "updated": 0, "errors": 0}

    with transaction.atomic():
        for row in reader:
            try:
                handle = row.get('Handle') or slugify(row.get('Name', ''))
                if not handle:
                    continue

                # 1. Get or Create Product
                product, created = Product.objects.get_or_create(
                    shop_id=shop_id,
                    slug=handle,
                    defaults={
                        'tenant_id': shop_id,
                        'name': row.get('Name'),
                        'description': row.get('Description', ''),
                        'base_price': Decimal(row.get('Base Price', '0')),
                        'purchase_price': Decimal(row.get('Purchase Price', '0')),
                        'status': row.get('Status', 'DRAFT'),
                    }
                )

                if not created:
                    # Update product fields if provided
                    if row.get('Name'): product.name = row.get('Name')
                    if row.get('Base Price'): product.base_price = Decimal(row.get('Base Price'))
                    product.save()
                    stats["updated"] += 1
                else:
                    stats["created"] += 1

                # 2. Handle Category
                cat_name = row.get('Category')
                if cat_name:
                    category, _ = Category.objects.get_or_create(
                        shop_id=shop_id, 
                        name=cat_name,
                        defaults={'tenant_id': shop_id, 'slug': slugify(cat_name)}
                    )
                    product.category = category
                    product.save()

                # 3. Handle Variant
                sku = row.get('Variant SKU')
                if sku:
                    variant, v_created = ProductVariant.objects.update_or_create(
                        shop_id=shop_id,
                        sku=sku,
                        defaults={
                            'tenant_id': shop_id,
                            'product': product,
                            'attribute_name_1': row.get('Variant Attr 1 Name', ''),
                            'attribute_value_1': row.get('Variant Attr 1 Value', ''),
                            'attribute_name_2': row.get('Variant Attr 2 Name', ''),
                            'attribute_value_2': row.get('Variant Attr 2 Value', ''),
                            'price_override': Decimal(row.get('Variant Price Override')) if row.get('Variant Price Override') else None,
                            'stock_quantity': int(row.get('Variant Stock', '0')) if row.get('Variant Stock') else 0,
                        }
                    )
            except Exception as e:
                stats["errors"] += 1
                continue

    return stats
