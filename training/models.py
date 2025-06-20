from django.db import models

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
    user = models.CharField(max_length=100)
    project_name = models.CharField(max_length=100)
    pre_model_name = models.CharField(max_length=100)
    dataset_name = models.CharField(max_length=100)
    task_type = models.CharField(max_length=132)
    status = models.CharField(max_length=16)
    epoch = models.IntegerField()
    batch_size = models.IntegerField()
    image_size = models.IntegerField()
    create_time = models.DateTimeField(auto_now_add=True)
    model_size = models.CharField(max_length=32)

class TrainingEpochModel(models.Model):
    id = models.AutoField(primary_key=True)
    training_model = models.ForeignKey(TrainingModel, on_delete=models.CASCADE)
    epoch_number = models.IntegerField()
    mAP50 = models.FloatField()
    mAP95 = models.FloatField()
    precision = models.FloatField()
    recall = models.FloatField()
    create_time = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['training_model', 'epoch_number']
    
    @classmethod
    def get_latest_epoch(cls, training_id):
        return cls.objects.filter(training_model__id=training_id).order_by('-epoch_number').first()

# Create your models here.
