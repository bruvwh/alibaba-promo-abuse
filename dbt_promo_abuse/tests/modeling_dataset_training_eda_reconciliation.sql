-- Reconcile only training outcomes against the already-reviewed EDA.
select count(*) as observations, sum(abuse_next_7d) as positives
from {{ ref('user_modeling_dataset') }}
where dataset_split = 'train'
having count(*) != 483431 or sum(abuse_next_7d) != 5552
