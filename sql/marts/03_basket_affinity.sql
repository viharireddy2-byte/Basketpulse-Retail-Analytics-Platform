-- Market-basket affinity over the trailing 90 days: support / confidence / lift and *basket margin*.
-- Apriori-style pruning keeps pair explosion bounded: only frequent items participate in pairs.
DECLARE as_of DATE DEFAULT (SELECT MAX(transaction_date) FROM `{{project}}.{{dataset}}.fct_transactions`);
DECLARE min_item_tx INT64 DEFAULT {{min_item_support}};
DECLARE min_pair_tx INT64 DEFAULT {{min_pair_support}};

CREATE OR REPLACE TABLE `{{project}}.{{dataset}}.basket_affinity`
CLUSTER BY product_a, product_b
AS
WITH baskets AS (
  SELECT transaction_id, basket_margin_amount,
         ARRAY(SELECT DISTINCT li.product_id FROM UNNEST(line_items) AS li) AS products
  FROM `{{project}}.{{dataset}}.fct_transactions`
  WHERE transaction_date > DATE_SUB(as_of, INTERVAL 90 DAY) AND basket_lines BETWEEN 2 AND 30
), n_total AS (SELECT COUNT(*) AS n FROM baskets),
item_support AS (
  SELECT product_id, COUNT(*) AS item_tx
  FROM baskets, UNNEST(products) AS product_id
  GROUP BY product_id HAVING COUNT(*) >= min_item_tx
), pruned AS (
  SELECT transaction_id, ANY_VALUE(basket_margin_amount) AS basket_margin_amount, ARRAY_AGG(product_id) AS products
  FROM baskets, UNNEST(products) AS product_id
  JOIN item_support USING (product_id)
  GROUP BY transaction_id HAVING COUNT(*) >= 2
), pairs AS (
  SELECT a AS product_a, b AS product_b, COUNT(*) AS pair_tx, AVG(basket_margin_amount) AS avg_basket_margin
  FROM pruned, UNNEST(products) AS a, UNNEST(products) AS b
  WHERE a < b
  GROUP BY a, b HAVING COUNT(*) >= min_pair_tx
)
SELECT p.product_a, p.product_b, p.pair_tx,
  p.pair_tx / n.n                                           AS support,
  SAFE_DIVIDE(p.pair_tx, ia.item_tx)                        AS confidence_a_to_b,
  SAFE_DIVIDE(p.pair_tx, ib.item_tx)                        AS confidence_b_to_a,
  SAFE_DIVIDE(p.pair_tx * n.n, ia.item_tx * ib.item_tx)     AS lift,
  p.avg_basket_margin, as_of AS as_of_date
FROM pairs AS p CROSS JOIN n_total AS n
JOIN item_support AS ia ON ia.product_id = p.product_a
JOIN item_support AS ib ON ib.product_id = p.product_b;
