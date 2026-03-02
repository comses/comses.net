---
applyTo: "**/permissions.py,**/backends.py"
---

# Permissions and Auth

## Overview

CoMSES Net uses a three-layer permission system: allauth for authentication, a custom `ComsesObjectPermissionBackend` for owner/published logic, and django-guardian for per-object permissions. Social login is supported via ORCID, GitHub, and Google. See `comses-overview.mdc` for stack context.

## Architecture

### Permission Check Resolution Order

When `user.has_perm(perm, obj)` is called, Django checks backends in order:

```
1. allauth.account.auth_backends.AuthenticationBackend
   -> Handles login authentication (email/password + social)
   -> Does NOT handle object permissions

2. core.backends.ComsesObjectPermissionBackend
   -> Only handles models registered via add_to_comses_permission_whitelist()
   -> Only handles add_, change_, delete_, view_ permissions
   -> Resolution (checked in this order, first True wins):
      a. Active user + non-object action (add_) -> True
      b. delete_ action on non-deletable object -> raises PermissionDenied
      c. view_ action + object is published (live=True) -> True
      d. view_ action + user has ANY guardian perm on object -> True
      e. user is the submitter (owner) of the object -> True

3. guardian.backends.ObjectPermissionBackend
   -> Per-object permissions assigned via django-guardian
   -> Fallback for anything not handled by #2
```

### Key Files

```
django/core/
  backends.py      # ComsesObjectPermissionBackend, add_to_comses_permission_whitelist()
  permissions.py   # DRF permission classes: ObjectPermissions, ViewRestrictedObjectPermissions, ModeratorPermissions
  models.py        # ComsesGroups enum
  queryset.py      # PUBLISHED_ATTRIBUTE_KEY, OWNER_ATTRIBUTE_KEY, DELETABLE_ATTRIBUTE_KEY constants
```

## Patterns

### `ComsesObjectPermissionBackend`

The custom backend at `core/backends.py` handles object-level permission logic:

```python
# core/backends.py line 110
class ComsesObjectPermissionBackend:
    HANDLED_PERMS = re.compile("add_|change_|delete_|view_")

    def has_perm(self, user, perm, obj=None):
        if not user.is_active and not user.is_anonymous:
            raise PermissionDenied

        model = get_model(perm)
        if model in HANDLED_MODELS and re.search(self.HANDLED_PERMS, perm):
            return (
                has_authenticated_model_permission(user, perm, obj)
                or has_delete_permission(perm, obj)
                or has_view_permission(perm, user, obj)
                or has_submitter_permission(user, obj)
            )
        else:
            return False  # defer to next backend (guardian)
```

### Model Whitelist Registration

Models must be explicitly registered to use the custom backend:

```python
# core/backends.py line 102
HANDLED_MODELS = set()

def add_to_comses_permission_whitelist(model):
    """Include model permissions checking for the ComsesObjectPermissionBackend"""
    HANDLED_MODELS.add(model)
    return model

# Usage (as decorator on model class):
@add_to_comses_permission_whitelist
class Event(index.Indexed, ClusterableModel):
    ...
```

### Queryset Attribute Constants

```python
# core/queryset.py
PUBLISHED_ATTRIBUTE_KEY = "live"         # model.live = True means published
DELETABLE_ATTRIBUTE_KEY = "deletable"    # model.deletable = False prevents deletion
OWNER_ATTRIBUTE_KEY = "submitter"        # model.submitter = owner user
```

### `ComsesGroups` Enum

Manages Django auth groups with convenience methods:

```python
# core/models.py line 40
class ComsesGroups(Enum):
    ADMIN = "Admins"
    MODERATOR = "Moderators"
    EDITOR = "Editors"
    FULL_MEMBER = "Full Members"

    @staticmethod
    @transaction.atomic
    def initialize():
        return [Group.objects.get_or_create(name=g.value)[0] for g in ComsesGroups]

    def is_member(self, user):
        return ComsesGroups.is_group_member(user, self.value)

    def set_membership(self, user: User, value: bool):
        if value:
            self.add(user)
        else:
            self.remove(user)

    @staticmethod
    def is_moderator(user):
        return ComsesGroups.MODERATOR.is_member(user)

    @staticmethod
    def is_full_member(user):
        return ComsesGroups.FULL_MEMBER.is_member(user)
```

### DRF Permission Classes

```python
# core/permissions.py

class ObjectPermissions(permissions.DjangoObjectPermissions):
    """Base class with relaxed perms_map. GET/OPTIONS/HEAD require no permissions.
    POST requires add_. PUT/PATCH require change_ (at object level). DELETE requires delete_ (at object level)."""
    authenticated_users_only = False

class ViewRestrictedObjectPermissions(ObjectPermissions):
    """Same as ObjectPermissions but GET also requires view_ permission at object level.
    Used for draft/unpublished content that should not be publicly visible."""
    # object_perms_map["GET"] = ["%(app_label)s.view_%(model_name)s"]

class ModeratorPermissions(permissions.BasePermission):
    """Allows access only to superusers or members of the Moderators group."""
    def has_permission(self, request, view):
        user = request.user
        if user and user.is_authenticated:
            return user.is_superuser or ComsesGroups.is_moderator(user)
        return False
```

### `PermissionRequiredByHttpMethodMixin`

Used by `FormUpdateView`, `FormCreateView`, and `FormMarkDeletedView` for non-ViewSet views:

```python
# core/mixins.py line 92
class PermissionRequiredByHttpMethodMixin:
    namespace = None
    model = None
    ext = "jinja"

    def get_required_permissions(self, request=None):
        perms = ViewRestrictedObjectPermissions.get_required_object_permissions(
            self.method, self.model
        )
        return perms

    def dispatch(self, request, *args, **kwargs):
        # checks permissions before dispatching
        response = self.check_permissions()
        if response:
            return response  # redirect to login or raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)
```

### Social Login (allauth)

Configured in `defaults.py`:

```python
SOCIALACCOUNT_PROVIDERS = {
    "github": {"SCOPE": ["read:user", "user:email", "read:org"]},
    "orcid": {"BASE_DOMAIN": "sandbox.orcid.org", "MEMBER_API": True},
    # Google configured via allauth admin
}
# NOTE: orcid BASE_DOMAIN is overridden in production.py to "orcid.org"
```

Social auth secrets use `read_secret()`:
```python
ORCID_CLIENT_SECRET = read_secret("orcid_client_secret")
GITHUB_CLIENT_SECRET = read_secret("github_client_secret")
```

## Gotchas

- **Owner always has permission.** `has_submitter_permission()` checks `obj.submitter == user`. If your model uses a different field for ownership, this won't work -- you must use the `submitter` field name or modify the backend.
- **Published means viewable by everyone.** If `obj.live == True`, any user (including anonymous) can view it. This is checked BEFORE guardian permissions.
- **Models must be whitelisted.** If you forget `@add_to_comses_permission_whitelist` on a model, the custom backend returns `False` and defers everything to guardian. The model won't get the owner/published shortcuts.
- **Non-deletable objects raise `PermissionDenied`.** If `obj.deletable` is `False`, attempting to delete raises `PermissionDenied` regardless of user permissions.
- **`ObjectPermissions` allows unauthenticated users.** `authenticated_users_only = False` means anonymous users can make GET requests. Use `ViewRestrictedObjectPermissions` when even viewing requires permission.
- **Group membership is checked via DB query.** `ComsesGroups.is_member(user)` does `user.groups.filter(name=...).exists()` -- it's not cached.

## Extension

### Adding a new permission-controlled model

1. Add `submitter` FK to User on the model
2. Add `live` BooleanField if the model has draft/published states
3. Add `deletable` property if some instances should be non-deletable
4. Decorate the model class with `@add_to_comses_permission_whitelist`
5. Use `ObjectPermissions` or `ViewRestrictedObjectPermissions` on the ViewSet
6. Assign guardian permissions in `perform_create()` if needed
