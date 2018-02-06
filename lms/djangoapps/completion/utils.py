# Django imports
from django.core.urlresolvers import reverse

# edX imports
from lms.djangoapps.completion.models import BlockCompletion

def get_url_to_last_completed_block(user, enrollment):
    '''Throws exception if LastCompletedBlock is None'''
    LastCompletedBlock = BlockCompletion.get_latest_block_completed(user, enrollment.course_id)
    urlToBlock = reverse('jump_to', kwargs={'course_id': enrollment.course_id, 'location': LastCompletedBlock.block_key})
    return urlToBlock