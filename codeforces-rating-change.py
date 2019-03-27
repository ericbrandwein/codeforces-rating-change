"""
Calculates the expected standing and the expected rating change for a user
given the actual standing in a Codeforces competition.

See https://codeforces.com/blog/entry/20762.
"""
from codeforces.api.codeforces_api import CodeforcesAPI
from codeforces.api.json_objects.contest import ContestPhase
from math import ceil, sqrt, floor
import sys

MAX_RATING = 5000  # arbitrary number, tourist's rating is ~3600


class Bounds:
    def __init__(self, first_bound, second_bound):
        if first_bound < second_bound:
            self.lower_bound = first_bound
            self.upper_bound = second_bound
        else:
            self.lower_bound = second_bound
            self.upper_bound = first_bound

    def get_middle(self):
        return (self.upper_bound + self.lower_bound) / 2

    def same_bounds(self):
        return self.lower_bound == self.upper_bound


def search_rating_for(
        rating_bounds, desired_standing, participant_ratings):
    middle_rating = ceil(rating_bounds.get_middle())
    if rating_bounds.same_bounds():
        found_rating = middle_rating
    else:
        expected_standing = get_expected_standing(
            middle_rating, participant_ratings)

        if expected_standing == desired_standing:
            found_rating = middle_rating
        else:
            if expected_standing < desired_standing:
                # If the standing is lower in number than the one desired,
                # the rating should be lower.
                rating_bounds.upper_bound = middle_rating - 1
            else:
                # expected_standing > desired_standing
                # If the standing is higher in number than the one desired,
                # the rating should be higher.
                if middle_rating == rating_bounds.upper_bound:
                    rating_bounds.lower_bound = middle_rating
                else:
                    rating_bounds.lower_bound = middle_rating + 1
            found_rating = search_rating_for(
                rating_bounds, desired_standing, participant_ratings)

    return found_rating


# El rating se está calculando mal porque no estoy tomando en
# cuenta el ajuste que se hace para que no haya inflación.
# El código en C++ está en https://codeforces.com/contest/1/submission/13861109,
# en la función process().
def get_expected_rating_change(
        expected_standing, actual_standing, previous_rating, participant_ratings):
    mean_standing = floor(sqrt(expected_standing * actual_standing))
    if mean_standing < actual_standing:
        other_bound = 0
    else:
        other_bound = MAX_RATING
    rating_search_bounds = Bounds(other_bound, previous_rating)

    calculated_rating = search_rating_for(
        rating_search_bounds, mean_standing, participant_ratings)

    expected_rating_change = int((calculated_rating - previous_rating) / 2)

    return expected_rating_change


def get_current_participant_rating(handle):
    participant_rating_changes = list(api.user_rating(handle))
    rating = 0
    if participant_rating_changes:
        rating = participant_rating_changes[-1].new_rating
    return rating


def handle_of_row(row):
    return row.party.members[0].handle


def probability_of_greater_rank(first_rating, second_rating):
    rating_difference = second_rating - first_rating
    return 1 / (1 + 10 ** (rating_difference / 400))


def get_expected_standing(my_rating, participant_ratings):
    expected_standing = 1
    for other_rating in participant_ratings:
        expected_standing += probability_of_greater_rank(
            other_rating, my_rating)

    return expected_standing


def retrieve_ratings_from_current_ratings(api, handles, my_handle):
    # We have to split the handles in blocks of 500 because otherwise
    # the API explodes.
    ratings = []
    for i in range(0, len(handles), 500):
        ratings += [
            user.rating for user in api.user_info(handles[i:i + 500])
        ]

    my_rating = get_current_participant_rating(my_handle)
    return my_rating, ratings


def retrieve_ratings_from_rating_changes(api, contest_id, my_handle):
    rating_changes = api.contest_rating_changes(contest_id)
    rating_changes_list = list(rating_changes)
    my_rating = None
    previous_ratings = []
    for rating_change in rating_changes_list:
        if rating_change.handle == my_handle:
            my_rating = rating_change.old_rating
        else:
            previous_ratings.append(rating_change.old_rating)
    return my_rating, previous_ratings


contest_id = int(sys.argv[1])
handle = sys.argv[2]

api = CodeforcesAPI()
print('Retrieving standings...')
standings = api.contest_standings(contest_id)
print('Standings retrieved!')

participants = list(standings['rows'])

print('Retrieving ratings...')
contest = standings['contest']
if contest.phase == ContestPhase.finished:
    my_rating, participant_ratings = retrieve_ratings_from_rating_changes(
        api, contest_id, handle)
else:
    participant_handles = [
        handle_of_row(participant) for participant in participants
        if handle_of_row(participant) != handle
    ]
    my_rating, participant_ratings = retrieve_ratings_from_current_ratings(
        api, participant_handles, handle)
print('Ratings retrieved!')


expected_standing = get_expected_standing(my_rating, participant_ratings)

actual_standing = [
    participant.rank for participant in participants if handle_of_row(participant) == handle
][0]

rating_change = get_expected_rating_change(
    expected_standing, actual_standing, my_rating, participant_ratings)

GREEN_TEXT_BLOCK = '\033[1;32;40m'
RED_TEXT_BLOCK = '\033[1;31;40m'
END_BLOCK = '\033[1;0;0m'

if rating_change >= 0:
    rating_change_string = '+' + str(rating_change)
    if rating_change > 0:
        rating_change_string = GREEN_TEXT_BLOCK + rating_change_string + END_BLOCK
else:
    rating_change_string = RED_TEXT_BLOCK + str(rating_change) + END_BLOCK

print('Expected standing: {}'.format(expected_standing))
print('Actual standing: {}'.format(actual_standing))
print('Expected rating change: {} ({} -> {})'.format(
    rating_change_string, my_rating, my_rating + rating_change))
if actual_standing <= expected_standing:
    print("You did well!")
else:
    print("You did badly :(")
