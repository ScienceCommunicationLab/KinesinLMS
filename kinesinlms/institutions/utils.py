from slugify import slugify

from kinesinlms.institutions.models import Institution


def setup_byrc_institutions():
    for institution_name in [
        "Case Western Biomedical",
        "CU Anschutz Biomedical",
        "Ponce Health Sci RISE",
        "UNC Biological Biomedical Sci",
        "U Chicago IMSD",
        "UVA Biomedical Sci",
        "UCSF Propel",
        "U Chicago PREP",
        "U Missouri PREP",
        "Brooklyn College MARC",
        "FIU MARC",
        "FIU McNair",
        "ODU MARC",
        "U Hawaii INBRE",
        "U Hawaii Natural Sci (PB)",
        "U Iowa Biosciences Academy",
        "UTEP RISE"
    ]:
        institution, created = Institution.objects.get_or_create(name=institution_name)
        institution.slug = slugify(institution.name)
        institution.save()
        if created:
            print(f" - CREATED '{institution_name}'")
        else:
            print(f" - SKIPPED existing '{institution_name}'")
