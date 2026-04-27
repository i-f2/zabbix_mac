-- 更新hosts表，添加系统名称和模块名称字段

ALTER TABLE hosts
ADD COLUMN system VARCHAR(100),
ADD COLUMN subsystem VARCHAR(100);

-- 提交事务
COMMIT;