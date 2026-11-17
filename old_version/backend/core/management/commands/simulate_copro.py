"""Opt-in synthetic data; no reset, deletion, external notification or bank order."""
import json
import os
from pathlib import Path
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from finance.models import Organization, FiscalYear
from core.access import is_manager
from core.demo import DemoScenario


class Command(BaseCommand):
    help='Préparer et vérifier une vie fictive DÉMO 2025–2026. Sans --apply : aucun changement.'

    def add_arguments(self,parser):
        parser.add_argument('--apply',action='store_true')
        parser.add_argument('--user',default='admin')
        parser.add_argument('--with-access',action='store_true')
        parser.add_argument('--access-file',help='Fichier privé des mots de passe temporaires, à conserver hors du dépôt.')
        parser.add_argument('--report-file',help='Rapport JSON sans mots de passe.')

    def handle(self,*args,**options):
        if not options['apply']:
            self.stdout.write('Aperçu : 5 copropriétaires, 6 lots, appels courants/travaux/fonds, paiements, banque, clôture et 2 AG DÉMO. Aucune donnée modifiée. Utiliser --apply après sauvegarde.')
            return
        if options['with_access'] and not options['access_file']:raise CommandError('--with-access exige --access-file, hors du dépôt public.')
        user=get_user_model().objects.filter(username=options['user']).first()
        if not user or not is_manager(user):raise CommandError('Choisissez un compte gestionnaire existant avec --user.')
        scenario=DemoScenario(user);outputs=[]
        try:
            with transaction.atomic():
                Organization.objects.get_or_create(pk=1)
                Organization.objects.select_for_update().get(pk=1)
                list(FiscalYear.objects.select_for_update().order_by('id'))
                report,credentials,created=scenario.run(with_access=options['with_access'])
                if credentials:
                    path=Path(options['access_file']);path.parent.mkdir(parents=True,exist_ok=True)
                    text='# Accès fictifs Copro. — privés\n\nMots de passe temporaires : changement demandé à la première connexion.\n\n'
                    text+='\n'.join('## '+r['name']+'\n\n- Courriel : '+r['email']+'\n- Mot de passe temporaire : `'+r['temporary_password']+'`\n' for r in credentials)
                    with path.open('x',encoding='utf-8',newline='\n') as stream:stream.write(text)
                    os.chmod(path,0o600);outputs.append(path)
                if options['report_file']:
                    path=Path(options['report_file']);path.parent.mkdir(parents=True,exist_ok=True)
                    path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
            self.stdout.write(('Simulation créée.' if created else 'Simulation déjà présente : aucune duplication, aucun mot de passe réinitialisé.')+' '+str(len(report['owners']))+' copropriétaires DÉMO ; '+str(report['calls'])+' appels ; '+str(sum(c['ok'] for c in report['checks']))+'/'+str(len(report['checks']))+' contrôles concordants.')
            if credentials:self.stdout.write('Accès temporaires écrits dans le fichier privé demandé ; aucun mot de passe affiché dans le journal.')
        except Exception as error:
            scenario.cleanup_files()
            for path in outputs:path.unlink(missing_ok=True)
            if isinstance(error,CommandError):raise
            raise CommandError(str(error)) from error
