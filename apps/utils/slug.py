from django.utils.text import slugify


def get_next_unique_slug(
    model_class, display_name, slug_field_name, extra_filter_args=None
):
    """
    Gets the next unique slug based on the name. Appends -1, -2, etc. until it finds
    a unique value.
    """
    base_value = slugify(display_name)
    return get_next_unique_slug_value(
        model_class, base_value, slug_field_name, extra_filter_args
    )


def get_next_unique_slug_value(
    model_class, slug_value, slug_field_name, extra_filter_args=None
):
    """
    Gets the next unique slug based on the value. Appends -1, -2, etc. until it finds
    a unique value.
    """
    extra_filter_args = extra_filter_args or dict()
    filter_kwargs = extra_filter_args.copy()
    filter_kwargs[slug_field_name] = slug_value
    if model_class.objects.filter(**filter_kwargs).exists():
        # todo make this do fewer queries
        suffix = 2
        while True:
            next_slug = get_next_slug(slug_value, suffix)
            filter_kwargs[slug_field_name] = next_slug
            if not model_class.objects.filter(**filter_kwargs).exists():
                return next_slug
            else:
                suffix += 1
    else:
        return slug_value


def get_next_slug(base_value, suffix, max_length=100):
    """
    Gets the next slug from base_value such that "base_value-suffix" will not exceed max_length characters.
    """
    suffix_length = len(str(suffix)) + 1  # + 1 for the "-" character
    if suffix_length >= max_length:
        raise ValueError(
            "Suffix {} is too long to create a unique slug! ".format(suffix)
        )

    return "{}-{}".format(base_value[: max_length - suffix_length], suffix)
