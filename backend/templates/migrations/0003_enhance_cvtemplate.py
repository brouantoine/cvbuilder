# Generated migration for enhanced CVTemplate

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('templates', '0002_add_docx_filename'),
    ]

    operations = [
        migrations.AddField(
            model_name='cvtemplate',
            name='category',
            field=models.CharField(
                choices=[
                    ('classic', 'Classique'),
                    ('modern', 'Moderne'),
                    ('creative', 'Créatif'),
                    ('minimal', 'Minimaliste'),
                    ('colorful', 'Coloré'),
                ],
                default='classic',
                max_length=50,
            ),
        ),
        migrations.AddField(
            model_name='cvtemplate',
            name='long_description',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='cvtemplate',
            name='thumbnail',
            field=models.ImageField(
                blank=True,
                help_text='Image miniature pour la grille (200x280px)',
                null=True,
                upload_to='templates/thumbnails/',
            ),
        ),
        migrations.AddField(
            model_name='cvtemplate',
            name='preview_full',
            field=models.ImageField(
                blank=True,
                help_text='Aperçu haute résolution (1200x1697px A4)',
                null=True,
                upload_to='templates/previews/',
            ),
        ),
        migrations.AddField(
            model_name='cvtemplate',
            name='is_active',
            field=models.BooleanField(default=True, help_text='Si désactivé, le template ne s\'affiche pas'),
        ),
        migrations.AddField(
            model_name='cvtemplate',
            name='order',
            field=models.PositiveIntegerField(
                default=0,
                help_text='Ordre d\'affichage (0=premier)',
            ),
        ),
        migrations.AlterModelOptions(
            name='cvtemplate',
            options={
                'ordering': ['order', 'name'],
                'verbose_name': 'Template CV',
                'verbose_name_plural': 'Templates CV',
            },
        ),
    ]
