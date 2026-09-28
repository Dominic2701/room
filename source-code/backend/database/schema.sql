CREATE DATABASE IF NOT EXISTS `dominic` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE `dominic`;

CREATE TABLE IF NOT EXISTS `user` (
    user_id BIGINT PRIMARY KEY AUTO_INCREMENT,
    full_name VARCHAR(150) NOT NULL,
    email VARCHAR(254) NOT NULL UNIQUE,
    phone VARCHAR(20) NOT NULL,
    username VARCHAR(150) NOT NULL UNIQUE,
    password_hash VARCHAR(128) NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS residency (
    residency_id BIGINT PRIMARY KEY AUTO_INCREMENT,
    residency_name VARCHAR(150) NOT NULL UNIQUE,
    provider_name VARCHAR(150) NOT NULL,
    location VARCHAR(200) NOT NULL,
    address TEXT NOT NULL,
    description TEXT NOT NULL,
    phone VARCHAR(30) NOT NULL,
    email VARCHAR(254) NOT NULL,
    main_image VARCHAR(255) NOT NULL,
    status VARCHAR(10) NOT NULL DEFAULT 'ACTIVE',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT residency_status_ck CHECK (status IN ('ACTIVE', 'INACTIVE'))
);

CREATE TABLE IF NOT EXISTS `admin` (
    admin_id BIGINT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(150) NOT NULL UNIQUE,
    password_hash VARCHAR(128) NOT NULL,
    status VARCHAR(10) NOT NULL DEFAULT 'ACTIVE',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT admin_status_ck CHECK (status IN ('ACTIVE', 'INACTIVE'))
);

CREATE TABLE IF NOT EXISTS admin_residencies (
    admin_id BIGINT NOT NULL,
    residency_id BIGINT NOT NULL,
    PRIMARY KEY (admin_id, residency_id),
    CONSTRAINT admin_residencies_admin_fk FOREIGN KEY (admin_id) REFERENCES `admin`(admin_id),
    CONSTRAINT admin_residencies_residency_fk FOREIGN KEY (residency_id) REFERENCES residency(residency_id)
);

CREATE TABLE IF NOT EXISTS room_details (
    room_id BIGINT PRIMARY KEY AUTO_INCREMENT,
    residency_id BIGINT NOT NULL,
    room_number INT NOT NULL,
    room_type VARCHAR(20) NOT NULL,
    price_per_night DECIMAL(10,2) NOT NULL,
    total_rooms INT UNSIGNED NOT NULL,
    available_rooms INT UNSIGNED NOT NULL,
    capacity INT UNSIGNED NOT NULL,
    description TEXT NOT NULL,
    status VARCHAR(12) NOT NULL DEFAULT 'AVAILABLE',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY room_residency_number_uk (residency_id, room_number),
    CONSTRAINT room_price_ck CHECK (price_per_night > 0),
    CONSTRAINT room_inventory_ck CHECK (available_rooms <= total_rooms),
    CONSTRAINT room_status_ck CHECK (status IN ('AVAILABLE', 'MAINTENANCE', 'INACTIVE')),
    CONSTRAINT room_residency_fk FOREIGN KEY (residency_id) REFERENCES residency(residency_id),
    INDEX room_search_idx (residency_id, room_type, status)
);

CREATE TABLE IF NOT EXISTS gallery_image (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    residency_id BIGINT NULL,
    room_id BIGINT NULL,
    image VARCHAR(255) NOT NULL,
    image_type VARCHAR(12) NOT NULL DEFAULT 'OTHER',
    caption VARCHAR(150) NOT NULL DEFAULT '',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT gallery_image_one_parent_ck CHECK (
        (residency_id IS NOT NULL AND room_id IS NULL)
        OR (residency_id IS NULL AND room_id IS NOT NULL)
    ),
    CONSTRAINT gallery_image_residency_fk FOREIGN KEY (residency_id) REFERENCES residency(residency_id) ON DELETE CASCADE,
    CONSTRAINT gallery_image_room_fk FOREIGN KEY (room_id) REFERENCES room_details(room_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS booking_details (
    booking_id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id BIGINT NOT NULL,
    residency_id BIGINT NOT NULL,
    room_id BIGINT NOT NULL,
    booking_reference VARCHAR(32) NOT NULL UNIQUE,
    check_in DATE NOT NULL,
    check_out DATE NOT NULL,
    number_of_rooms INT UNSIGNED NOT NULL,
    number_of_guests INT UNSIGNED NOT NULL,
    price_per_night DECIMAL(10,2) NOT NULL,
    number_of_nights INT UNSIGNED NOT NULL,
    total_amount DECIMAL(12,2) NOT NULL,
    booking_status VARCHAR(12) NOT NULL,
    payment_status VARCHAR(10) NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT booking_dates_ck CHECK (check_out > check_in),
    CONSTRAINT booking_rooms_ck CHECK (number_of_rooms > 0),
    CONSTRAINT booking_user_fk FOREIGN KEY (user_id) REFERENCES `user`(user_id),
    CONSTRAINT booking_residency_fk FOREIGN KEY (residency_id) REFERENCES residency(residency_id),
    CONSTRAINT booking_room_fk FOREIGN KEY (room_id) REFERENCES room_details(room_id),
    INDEX booking_user_idx (user_id, created_at),
    INDEX booking_residency_idx (residency_id, booking_status)
);
