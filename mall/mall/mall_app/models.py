from __future__ import unicode_literals

from six import with_metaclass
import warnings
from collections import OrderedDict
from django.core import checks
from django.db import models
from django.utils.translation import ugettext_lazy as _

from shop import deferred
from shop.models.fields import JSONField
from shop.models.customer import CustomerModel
from shop.models.product import BaseProduct
from shop.modifiers.pool import cart_modifiers_pool
from shop.money import Money


class CartItemManager(models.Manager):
    """
    Customized model manager for our CartItem model.
    """

    def get_or_create(self, **kwargs):
        """
        Create a unique cart item. If the same product exists already in the given cart,
        increase its quantity, if the product in the cart seems to be the same.
        """
        cart = kwargs.pop('cart')
        product = kwargs.pop('product')
        quantity = int(kwargs.pop('quantity', 1))

        # add a new item to the cart, or reuse an existing one, increasing the quantity
        watched = not quantity
        cart_item = product.is_in_cart(cart, watched=watched, **kwargs)
        if cart_item:
            if not watched:
                cart_item.quantity += quantity
            created = False
        else:
            cart_item = self.model(cart=cart, product=product, quantity=quantity, **kwargs)
            created = True

        cart_item.save()
        return cart_item, created

    def filter_cart_items(self, cart, request):
        """
        Use this method to fetch items for shopping from the cart. It rearranges the result set
        according to the defined modifiers.
        """
        cart_items = self.filter(cart=cart, quantity__gt=0).order_by('updated_at')
        for modifier in cart_modifiers_pool.get_all_modifiers():
            cart_items = modifier.arrange_cart_items(cart_items, request)
        return cart_items

    def filter_watch_items(self, cart, request):
        """
        Use this method to fetch items from the watch list. It rearranges the result set
        according to the defined modifiers.
        """
        watch_items = self.filter(cart=cart, quantity=0)
        for modifier in cart_modifiers_pool.get_all_modifiers():
            watch_items = modifier.arrange_watch_items(watch_items, request)
        return watch_items
