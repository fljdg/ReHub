from django.db import migrations


def copy_members(apps, schema_editor):
    StudyGroup = apps.get_model('core', 'StudyGroup')
    GroupMember = apps.get_model('core', 'GroupMember')

    for group in StudyGroup.objects.all():
        evaluator_set = False
        for user in group.members.all():
            is_creator = group.created_by_id is not None and user.pk == group.created_by_id
            GroupMember.objects.get_or_create(
                group=group,
                user=user,
                defaults={
                    'role': 'evaluator' if is_creator else 'member',
                    'status': 'active',
                    'joined_at': group.created_at,
                },
            )
            if is_creator:
                evaluator_set = True

        if not evaluator_set:
            # Never guess an evaluator. Fix it by hand in the admin site.
            print(f"\n  WARNING: group '{group.name}' (id {group.pk}) has no evaluator "
                  f"(created_by is empty or not a member). Set one in the admin site.")


def undo_copy(apps, schema_editor):
    GroupMember = apps.get_model('core', 'GroupMember')
    GroupMember.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0007_proposal_deadline_proposal_group_and_more'),
    ]

    operations = [
        migrations.RunPython(copy_members, undo_copy),
    ]