"""
catalog/services/data_ops/export.py

Service for exporting catalog data to CSV.
"""

import csv
import io
from typing import List
from catalog.models import Product, ProductVariant

def export_products_to_csv(shop_id: str) -> str:
    """
    Generates a CSV string of all active products and their variants.
    """
    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow([
        'Handle', 'Name', 'Description', 'Category', 'Status', 
        'Base Price', 'Purchase Price', 'Weight (g)', 
        'Variant SKU', 'Variant Attr 1 Name', 'Variant Attr 1 Value',
        'Variant Attr 2 Name', 'Variant Attr 2 Value',
        'Variant Price Override', 'Variant Stock'
    ])

    products = Product.objects.filter(shop_id=shop_id, deleted_at__isnull=True).prefetch_related('variants', 'category')

    for product in products:
        variants = product.variants.filter(deleted_at__isnull=True)
        
        # If no variants, write product info anyway
        if not variants.exists():
            writer.writerow([
                product.slug, product.name, product.description, 
                product.category.name if product.category else '',
                product.status, product.base_price, product.purchase_price,
                product.weight_grams or '',
                '', '', '', '', '', '', ''
            ])
            continue

        for variant in variants:
            writer.writerow([
                product.slug, product.name, product.description,
                product.category.name if product.category else '',
                product.status, product.base_price, product.purchase_price,
                product.weight_grams or '',
                variant.sku, variant.attribute_name_1, variant.attribute_value_1,
                variant.attribute_name_2, variant.attribute_value_2,
                variant.price_override or '',
                variant.stock_quantity
            ])

    return output.getvalue()
