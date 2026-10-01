from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0003_alter_evaluation_id_alter_milestone_id_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='ChapterSubmission',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('chapter', models.PositiveSmallIntegerField()),
                ('file', models.FileField(upload_to='chapters/')),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('approved', 'Approved'), ('revision', 'Needs Revision'), ('rejected', 'Rejected')], default='pending', max_length=20)),
                ('feedback', models.TextField(blank=True)),
                ('submitted_at', models.DateTimeField(auto_now=True)),
                ('proposal', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='chapters', to='core.proposal')),
            ],
            options={
                'ordering': ['chapter'],
                'unique_together': {('proposal', 'chapter')},
            },
        ),
    ]
