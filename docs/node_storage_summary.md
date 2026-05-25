# Node Storage Summary

## Cluster roles

| Container | Vai trò | Nội dung chính |
|---|---|---|
| `ecommerce-citus-coordinator` | Coordinator node | Lưu metadata phân tán, nhận query, lập kế hoạch truy vấn, điều phối task tới workers |
| `ecommerce-citus-worker-1` | Worker/data node | Lưu một phần shard placements của fact table và bản sao reference tables |
| `ecommerce-citus-worker-2` | Worker/data node | Lưu một phần shard placements của fact table và bản sao reference tables |
| `ecommerce-citus-worker-3` | Worker/data node | Lưu một phần shard placements của fact table và bản sao reference tables |
| `ecommerce-citus-worker-4` | Worker/data node | Lưu một phần shard placements của fact table và bản sao reference tables |

## Coordinator lưu gì?

Coordinator không phải nơi lưu dữ liệu phân tích chính. Coordinator lưu metadata phân tán, bao gồm:

- Danh sách worker nodes.
- Bảng nào là distributed table/reference table.
- Fact table có những shard nào.
- Mỗi shard có placements ở worker nào.
- Kế hoạch route query tới worker phù hợp.

Danh sách workers:

| nodeid | nodename | nodeport | isactive |
|---:|---|---:|---|
| 1 | `citus-worker-1` | 5432 | true |
| 2 | `citus-worker-2` | 5432 | true |
| 3 | `citus-worker-3` | 5432 | true |
| 4 | `citus-worker-4` | 5432 | true |

## Metadata phân phối dữ liệu

| Logical table | Shard count | Total placements | Placements per shard |
|---|---:|---:|---:|
| `fact_olist_orders` | 32 | 64 | 2 |
| `dim_customer` | 1 | 4 | 4 |
| `dim_seller` | 1 | 4 | 4 |
| `dim_product` | 1 | 4 | 4 |
| `dim_date` | 1 | 4 | 4 |
| `dim_payment` | 1 | 4 | 4 |
| `dim_review` | 1 | 4 | 4 |

## Worker nodes lưu gì?

`fact_olist_orders` được phân tán thật sự:

| Worker | Fact shard placements | Rows vật lý trên fact placements |
|---|---:|---:|
| `citus-worker-1` | 16 | 55,987 |
| `citus-worker-2` | 16 | 56,582 |
| `citus-worker-3` | 16 | 56,663 |
| `citus-worker-4` | 16 | 56,068 |

Các dimension/reference tables được replicate sang cả 4 workers:

| Table | Rows trên mỗi worker |
|---|---:|
| `dim_customer` | 99,441 |
| `dim_seller` | 3,095 |
| `dim_product` | 32,951 |
| `dim_date` | 751 |
| `dim_payment` | 99,440 |
| `dim_review` | 98,673 |

## Kết luận

Với 4 workers và `citus.shard_replication_factor = 2`, dữ liệu fact không còn bị copy toàn bộ lên mọi worker. Mỗi worker chỉ giữ 16 trong tổng số 64 fact shard placements, tương đương khoảng một nửa dữ liệu fact vật lý.

Mỗi fact shard có 2 bản sao trên 2 workers khác nhau. Vì vậy hệ thống vừa có phân tán dữ liệu thật sự, vừa có khả năng đọc đầy đủ dữ liệu khi một worker node bị sập.