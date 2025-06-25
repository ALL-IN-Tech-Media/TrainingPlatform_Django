from django.db import models
from accounts.models import User
from datasets.models import Dataset

class ProjectModel(models.Model):
    id = models.AutoField(primary_key=True)
    project_id = models.IntegerField()
    project_name = models.CharField(max_length=100)
    pre_trained_model = models.CharField(max_length=100)
    task_type = models.CharField(max_length=100)
    mAP = models.FloatField()
    status = models.CharField(max_length=100)
    model_size = models.CharField(max_length=100)
    create_time = models.DateTimeField(auto_now_add=True)


class TrainingModel(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE)
    model_name = models.CharField(max_length=100)
    training_type = models.CharField(max_length=100)
    epochs = models.IntegerField()
    batch_size = models.IntegerField()
    max_length = models.IntegerField()
    create_time = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=16)




class TrainingEpochModel(models.Model):
    id = models.AutoField(primary_key=True)
    training_model = models.ForeignKey(TrainingModel, on_delete=models.CASCADE)
    epoch_number = models.IntegerField()
    train_loss = models.FloatField()
    val_loss = models.FloatField()
    create_time = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['training_model', 'epoch_number']
    
    @classmethod
    def get_latest_epoch(cls, training_id):
        return cls.objects.filter(training_model__id=training_id).order_by('-epoch_number').first()

# Create your models here.
