CREATE
DATABASE IF NOT EXISTS dorm_management;
USE
dorm_management;

DROP TABLE IF EXISTS `payments`;
DROP TABLE IF EXISTS `contracts`;
DROP TABLE IF EXISTS `students`;
DROP TABLE IF EXISTS `rooms`;
DROP TABLE IF EXISTS `users`;

CREATE TABLE `users`
(
    `id`        int          NOT NULL AUTO_INCREMENT,
    `username`  varchar(50)  NOT NULL,
    `password`  varchar(255) NOT NULL,
    `full_name` varchar(100) DEFAULT NULL,
    `role`      enum('ADMIN','STAFF','STUDENT') DEFAULT NULL,
    PRIMARY KEY (`id`),
    UNIQUE KEY `ix_users_username` (`username`),
    KEY         `ix_users_id` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `rooms`
(
    `id`                int         NOT NULL AUTO_INCREMENT,
    `room_number`       varchar(20) NOT NULL,
    `room_type`         varchar(50) DEFAULT NULL,
    `capacity`          int         DEFAULT NULL,
    `current_occupancy` int         DEFAULT NULL,
    `price`             float       DEFAULT NULL,
    `status`            enum('AVAILABLE','OCCUPIED','MAINTENANCE') DEFAULT NULL,
    PRIMARY KEY (`id`),
    UNIQUE KEY `ix_rooms_room_number` (`room_number`),
    KEY                 `ix_rooms_id` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `students`
(
    `id`         int          NOT NULL AUTO_INCREMENT,
    `student_id` varchar(20)  NOT NULL,
    `full_name`  varchar(100) NOT NULL,
    `phone`      varchar(15)  DEFAULT NULL,
    `email`      varchar(100) DEFAULT NULL,
    `gender`     varchar(10)  DEFAULT NULL,
    `hometown`   varchar(100) DEFAULT NULL,
    `user_id`    int          DEFAULT NULL,
    `room_id`    int          DEFAULT NULL,
    PRIMARY KEY (`id`),
    UNIQUE KEY `ix_students_student_id` (`student_id`),
    KEY          `user_id` (`user_id`),
    KEY          `room_id` (`room_id`),
    KEY          `ix_students_id` (`id`),
    CONSTRAINT `students_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`),
    CONSTRAINT `students_ibfk_2` FOREIGN KEY (`room_id`) REFERENCES `rooms` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `contracts`
(
    `id`           int  NOT NULL AUTO_INCREMENT,
    `student_id`   int  NOT NULL,
    `room_id`      int  NOT NULL,
    `start_date`   date        DEFAULT NULL,
    `end_date`     date NOT NULL,
    `total_amount` float       DEFAULT NULL,
    `status`       varchar(20) DEFAULT NULL,
    PRIMARY KEY (`id`),
    KEY            `student_id` (`student_id`),
    KEY            `room_id` (`room_id`),
    KEY            `ix_contracts_id` (`id`),
    CONSTRAINT `contracts_ibfk_1` FOREIGN KEY (`student_id`) REFERENCES `students` (`id`),
    CONSTRAINT `contracts_ibfk_2` FOREIGN KEY (`room_id`) REFERENCES `rooms` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `payments`
(
    `id`           int   NOT NULL AUTO_INCREMENT,
    `contract_id`  int   NOT NULL,
    `amount`       float NOT NULL,
    `payment_type` enum('ROOM_FEE','ELECTRICITY','WATER') DEFAULT NULL,
    `payment_date` date         DEFAULT NULL,
    `status`       enum('PAID','UNPAID') DEFAULT NULL,
    `notes`        varchar(255) DEFAULT NULL,
    PRIMARY KEY (`id`),
    KEY            `contract_id` (`contract_id`),
    KEY            `ix_payments_id` (`id`),
    CONSTRAINT `payments_ibfk_1` FOREIGN KEY (`contract_id`) REFERENCES `contracts` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
