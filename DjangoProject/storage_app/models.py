from django.db import models
from django.contrib.auth.models import User

class StoredFile(models.Model):
    file_name = models.CharField(max_length=255)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    upload_date = models.DateTimeField(auto_now_add=True)
    file_size = models.BigIntegerField()
    checksum = models.CharField(max_length=64)  # Overall file checksum

    def __str__(self):
        return self.file_name

class FileChunk(models.Model):
    stored_file = models.ForeignKey(StoredFile, related_name='chunks', on_delete=models.CASCADE)
    chunk_number = models.IntegerField()
    file_path = models.CharField(max_length=500)  # Path where the chunk is stored
    checksum = models.CharField(max_length=64)    # Chunk checksum
    replicated = models.BooleanField(default=False)  # False = primary, True = replica

    def __str__(self):
        return f"{self.stored_file.file_name} - Chunk {self.chunk_number}"
