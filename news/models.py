from django.db import models
from members.models import Member


class Entry(models.Model):
    author = models.ManyToManyField(Member)
    headline = models.CharField(max_length=50)
    content = models.TextField()
    pub_date = models.DateTimeField(auto_now_add=True)

    def __unicode__(self):
        return self.headline
# Create your models here.