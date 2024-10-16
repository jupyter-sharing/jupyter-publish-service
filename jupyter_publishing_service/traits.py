import os
import typing as t

from traitlets import Bool, Int, TraitType, Undefined, Unicode


class FromEnvMixin:
    """A trait that pulls the value from an environment variable
    if it's given.
    """

    # Need to set the default_value to undefined, because
    # subclasses try to set their own default value
    # and prevents the dynamic default from working.
    default_value = Undefined
    _default_value_if_no_envvar = Undefined

    def __init__(self, name, default_value=None, help=None, *args, **kwargs):
        self.envvar_name = name
        self._default_value_if_no_envvar = default_value

        # Prefix the "help" string in these type of traits
        # with some documentation that mentions the
        # environment variable.
        help_prefix = f"(This trait is also configurable from the environment variable, {name}.) "
        if not help:
            help = help_prefix
        else:
            help = help_prefix + help
        # The actual traittype is second in the MRO.
        traittype = self.__class__.mro()[2]
        # traittype.__init__(self, help=help, *args, **kwargs)

    def make_dynamic_default(self):
        # Make sure to dynamically load the default when the
        # the trait is called.
        env_value = os.environ.get(self.envvar_name, None)
        if type(env_value) == str:
            env_value = env_value
        if env_value is None and self._default_value_if_no_envvar is not Undefined:
            return self._default_value_if_no_envvar

        return env_value


class UnicodeFromEnv(FromEnvMixin, Unicode):
    """Unicode Trait that pulls default value from environment variable."""


class IntFromEnv(FromEnvMixin, Int):
    """Unicode Trait that pulls default value from environment variable."""


class BoolFromEnv(FromEnvMixin, Bool):
    """Unicode Trait that pulls default value from environment variable."""
