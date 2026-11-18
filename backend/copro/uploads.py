from pathlib import Path
from .models import Attachment


def validate_files(files,existing=0):
    if len(files)+existing>8:raise ValueError('8 pièces jointes maximum par publication ou réponse.')
    if sum(file.size for file in files)>12*1024*1024:raise ValueError('12 Mo maximum pour l’ensemble des pièces.')
    allowed={'.pdf','.png','.jpg','.jpeg','.txt','.docx','.xlsx','.odt','.ods','.csv'}
    for file in files:
        if Path(file.name).suffix.lower() not in allowed or file.size>10*1024*1024:
            raise ValueError('Pièce jointe refusée : PDF, image, texte ou document bureautique de 10 Mo maximum.')


def write_files(post,files,stored,reply=None):
    for file in files:
        item=Attachment(post=post,reply=reply,name=Path(file.name).name[:200],size=file.size)
        item.file.save(file.name,file,save=False);stored.append(item.file);item.save()
