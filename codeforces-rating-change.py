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


class Competitor:
    def __init__(self, handle, actual_rank):
        self.handle = handle
        self.actual_rank = actual_rank
        self.expected_rank = None
        self.old_rating = None
        self.rating_change = None


def adjust_total_sum_zero(competitors):
    """
    Total sum of rating changes should not be more than zero.
    """
    rating_changes = [
        competitor.rating_change for competitor in competitors
    ]
    increment = int(-sum(rating_changes) / len(rating_changes) - 1)
    for competitor in competitors:
        competitor.rating_change += increment


def adjust_sum_of_top_zero(competitors):
    """
    Sum of top 4*sqrt ratings should be adjusted to zero.
    """
    competitors.sort(key=lambda comp: comp.old_rating, reverse=True)
    list_length = len(competitors)
    number_of_contestants_on_top = int(min(
        4 * round(sqrt(list_length)),
        list_length
    ))
    rating_change_sum = 0
    for competitor in competitors[:number_of_contestants_on_top]:
        rating_change_sum += competitor.rating_change

    increment = int(min(
        max(-rating_change_sum / number_of_contestants_on_top, -10),
        0
    ))
    for competitor in competitors:
        competitor.rating_change += increment


def adjust_rating_changes_for_inflation(competitors):
    adjust_total_sum_zero(competitors)
    adjust_sum_of_top_zero(competitors)


def search_rating_for(competitor_ratings, desired_standing, rating_bounds):
    while rating_bounds.upper_bound - rating_bounds.lower_bound > 1:
        middle_rating = ceil(rating_bounds.get_middle())
        expected_standing = get_expected_standing(
            middle_rating, competitor_ratings)
        if expected_standing < desired_standing:
            # If the standing is lower in number than the one desired,
            # the rating should be lower.
            rating_bounds.upper_bound = middle_rating
        else:
            # expected_standing > desired_standing
            # If the standing is higher in number than the one desired,
            # the rating should be higher.
            rating_bounds.lower_bound = middle_rating

    return rating_bounds.lower_bound


def rating_change_from_standing(competitor, competitors):
    mean_standing = floor(
        sqrt(competitor.expected_rank * competitor.actual_rank))

    if mean_standing < competitor.actual_rank:
        other_bound = 0
    else:
        other_bound = MAX_RATING
    rating_search_bounds = Bounds(other_bound, competitor.old_rating)

    competitors_ratings = [
        competitor.old_rating for competitor in competitors
    ]
    calculated_rating = search_rating_for(
        competitors_ratings, mean_standing, rating_search_bounds)

    expected_rating_change = int(
        (calculated_rating - competitor.old_rating) / 2)

    return expected_rating_change


def probability_of_greater_rank(first_rating, second_rating):
    rating_difference = second_rating - first_rating
    return 1 / (1 + 10 ** (rating_difference / 400))


def get_expected_standing(my_rating, competitor_ratings):
    expected_standing = 1
    for other_rating in competitor_ratings:
        expected_standing += probability_of_greater_rank(
            other_rating, my_rating)

    return expected_standing


def get_expected_competitor_standing(competitor, other_competitors):
    competitors_ratings = [
        competitor.old_rating for competitor in other_competitors
    ]
    return get_expected_standing(competitor.old_rating, competitors_ratings)


def load_rating_changes_from_old_ratings(competitors):
    for index, competitor in enumerate(competitors):
        competitors_without_current = [
            competitors[i] for i in range(len(competitors))
            if i != index
        ]
        competitor.expected_rank = get_expected_competitor_standing(
            competitor, competitors_without_current)
        competitor.rating_change = rating_change_from_standing(
            competitor, competitors)

    return adjust_rating_changes_for_inflation(competitors)


def retrieve_ratings_from_current_ratings(api, competitors):
    # We have to split the handles in blocks of 500 because otherwise
    # the API explodes.
    ratings = []
    increase = 500
    for i in range(0, len(competitors), increase):
        current_handles = [
            competitor.handle for competitor in competitors[i:i + increase]
        ]
        ratings += [
            user.rating for user in api.user_info(current_handles)
        ]

    return ratings


def retrieve_ratings_from_rating_changes(api, contest_id):
    rating_changes = api.contest_rating_changes(contest_id)
    rating_changes_list = list(rating_changes)
    my_rating = None
    previous_ratings = []
    for rating_change in rating_changes_list:
        previous_ratings.append(rating_change.old_rating)
    return previous_ratings


def load_old_ratings(api, contest, competitors):
    """
    Loads old_rating from the api into competitors.
    """
    if contest.phase == ContestPhase.finished:
        competitors_ratings = retrieve_ratings_from_rating_changes(
            api, contest.id)
    else:
        competitors_ratings = retrieve_ratings_from_current_ratings(
            api, competitors)

    for index, competitor in enumerate(competitors):
        competitor.old_rating = competitors_ratings[index]


def calculate_rating_changes(contest_id):
    api = CodeforcesAPI()
    print('Retrieving standings...')
    standings = api.contest_standings(contest_id)
    print('Standings retrieved!')

    competitors = [
        Competitor(row.party.members[0].handle, row.rank)
        for row in standings['rows']
    ]
    contest = standings['contest']

    print('Retrieving ratings...')
    load_old_ratings(api, contest, competitors)
    print('Ratings retrieved!')

    load_rating_changes_from_old_ratings(competitors)
    return competitors


contest_id = int(sys.argv[1])
handle = sys.argv[2]

competitors = calculate_rating_changes(contest_id)
my_competitor = [
    competitor for competitor in competitors if competitor.handle == handle
][0]

GREEN_TEXT_BLOCK = '\033[1;32;40m'
RED_TEXT_BLOCK = '\033[1;31;40m'
END_BLOCK = '\033[1;0;0m'

if my_competitor.rating_change >= 0:
    rating_change_string = '+' + str(my_competitor.rating_change)
    if my_competitor.rating_change > 0:
        rating_change_string = GREEN_TEXT_BLOCK + rating_change_string + END_BLOCK
else:
    rating_change_string = RED_TEXT_BLOCK + \
        str(my_competitor.rating_change) + END_BLOCK

print('Expected standing: {}'.format(my_competitor.expected_rank))
print('Actual standing: {}'.format(my_competitor.actual_rank))
print('Expected rating change: {} ({} -> {})'.format(
    rating_change_string, my_competitor.old_rating,
    my_competitor.old_rating + my_competitor.rating_change))
