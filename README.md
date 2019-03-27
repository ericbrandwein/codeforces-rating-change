# codeforces-rating-change

Calculates the rating change for participants of a Codeforces competition,
even when the competition isn't finished yet. Essentially a Python rewrite of
[the code used at Codeforces](https://codeforces.com/contest/1/submission/13861109).

The process used to calculate the rating change is described in
[this blogpost](https://codeforces.com/blog/entry/20762).

## Dependencies

- Python 3
- CodeforcesAPI: https://github.com/soon/CodeforcesAPI/

## Usage

```
> python codeforces-rating-change.py <contest-id> <handle>
```

For example, running:

```
> python codeforces-rating-change.py 1141 berocs
```

will give you this output:

```
Retrieving standings...
Standings retrieved!
Retrieving ratings...
Ratings retrieved!
Expected standing: 1550.1451660992382
Actual standing: 1722
Expected rating change: -6 (1564 -> 1558)
You did badly :(
```
