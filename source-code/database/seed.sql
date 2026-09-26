USE `dominic`;

INSERT INTO residency (residency_name, provider_name, location, description)
VALUES
    ('Grand Palace Residency', 'Grand Palace Hospitality', 'Chennai', 'Central Chennai rooms for business and leisure stays.'),
    ('Ocean View Residency', 'Ocean View Hospitality', 'Puducherry', 'Coastal rooms near the promenade.'),
    ('Green Park Residency', 'Green Park Hospitality', 'Bengaluru', 'Quiet city rooms with practical amenities.')
ON DUPLICATE KEY UPDATE provider_name = VALUES(provider_name), location = VALUES(location);

INSERT INTO room_details
    (residency_id, room_number, room_type, price_per_night, total_rooms, available_rooms, capacity, description)
SELECT residency_id, 101, 'SINGLE', 1500.00, 10, 10, 1, 'Comfortable single room.'
FROM residency WHERE residency_name = 'Grand Palace Residency'
ON DUPLICATE KEY UPDATE price_per_night = VALUES(price_per_night);

INSERT INTO room_details
    (residency_id, room_number, room_type, price_per_night, total_rooms, available_rooms, capacity, description)
SELECT residency_id, 201, 'DELUXE', 2500.00, 6, 6, 2, 'Deluxe room with room service.'
FROM residency WHERE residency_name = 'Grand Palace Residency'
ON DUPLICATE KEY UPDATE price_per_night = VALUES(price_per_night);

INSERT INTO room_details
    (residency_id, room_number, room_type, price_per_night, total_rooms, available_rooms, capacity, description)
SELECT residency_id, 301, 'DELUXE', 2800.00, 20, 20, 2, 'Ocean view deluxe room.'
FROM residency WHERE residency_name = 'Ocean View Residency'
ON DUPLICATE KEY UPDATE price_per_night = VALUES(price_per_night);

INSERT INTO room_details
    (residency_id, room_number, room_type, price_per_night, total_rooms, available_rooms, capacity, description)
SELECT residency_id, 401, 'FAMILY', 4000.00, 12, 12, 5, 'Family room for group stays.'
FROM residency WHERE residency_name = 'Green Park Residency'
ON DUPLICATE KEY UPDATE price_per_night = VALUES(price_per_night);
