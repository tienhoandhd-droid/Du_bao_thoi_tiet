# Eval Datasets

Chứa dataset manifest/version/hash và test cases không nhạy cảm. Golden questions
hiện ở `eval/golden-questions/`; migration eval v2 sẽ liên kết chúng với
`eval_datasets` thay vì di chuyển dữ liệu không cần thiết.

`r05_a39_eval_v2_failure_fixture.jsonl` là fixture âm local, không phải dataset
đã phê duyệt và không được seed bởi migration. Năm case synthetic ánh xạ
U10/U11/U13/U14/U15; mọi sai lệch phải fail closed và giữ evidence, không được
hạ threshold để tạo PASS.
