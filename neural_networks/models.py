from django.db import models

class NeuralNetwork(models.Model):
    name = models.CharField(max_length=100)
    layers = models.JSONField()  # 存储网络层信息
    created_at = models.DateTimeField(auto_now_add=True)
