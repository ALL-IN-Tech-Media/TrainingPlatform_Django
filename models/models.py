from django.db import models

# Create your models here.
class ModelFactory(models.Model):
    category = models.CharField(max_length=128)   # 第一层：LLM、CV、VLM等
    series = models.CharField(max_length=128)    # 第二层：Qwen、DeepSeek等
    model_name = models.CharField(max_length=255) # 第三层：Qwen2.5-0.5B-Instruct等
    config_info = models.JSONField(default=dict)
    description = models.TextField(blank=True)
    is_downloaded = models.BooleanField(default=False)
    status = models.CharField(max_length=128, default='')

    def __str__(self):
        return f"{self.category} - {self.series} - {self.model_name}"