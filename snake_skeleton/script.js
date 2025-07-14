const snakeContainer = document.getElementById('snake-container');
const snakeHeadImage = document.getElementById('snake-head-image');
const numSegments = 50; // Number of segments for the snake body
const segmentSize = 28; // Size of each segment (width, matching CSS)
const ribLength = 30; // Length of each rib (matching CSS)

let snake = [];

// Set the source for the snake head image
snakeHeadImage.src = 'snake_head.png';
snakeHeadImage.style.position = 'absolute';
snakeHeadImage.style.width = '65px'; /* Match CSS head width */
snakeHeadImage.style.height = '50px'; /* Match CSS head height */
snakeHeadImage.style.transformOrigin = 'center center';
snakeHeadImage.style.zIndex = '10';

snake.push({ element: snakeHeadImage, x: 400, y: 300, rotation: 0 }); // Initial position and rotation

// Create snake body segments
for (let i = 0; i < numSegments; i++) {
    const segment = document.createElement('div');
    segment.classList.add('snake-segment'); /* Add generic segment class */
    snakeContainer.appendChild(segment);
    snake.push({ element: segment, x: 400 - (i + 1) * segmentSize, y: 300, rotation: 0 });

    // Add ribs to each segment (except the head)
    for (let j = 0; j < 2; j++) { // Two ribs per segment
        const rib = document.createElement('div');
        rib.classList.add('snake-rib');
        segment.appendChild(rib);
    }
}

function updateSnakePosition() {
    snake.forEach((segment, index) => {
        if (index === 0) { // Head
            segment.element.style.left = `${segment.x - segment.element.offsetWidth / 2}px`;
            segment.element.style.top = `${segment.y - segment.element.offsetHeight / 2}px`;
            segment.element.style.transform = `rotate(${segment.rotation}deg)`;
        } else { // Body segments
            segment.element.style.left = `${segment.x - segmentSize / 2}px`;
            segment.element.style.top = `${segment.y - segmentSize / 2}px`;
            segment.element.style.transform = `rotate(${segment.rotation}deg)`;

            // Position ribs relative to the segment
            const ribs = segment.element.querySelectorAll('.snake-rib');
            if (ribs.length === 2) { /* Two ribs per segment */
                /* Rib 1 (left) */
                ribs[0].style.left = `${segmentSize / 2 - 2}px`; /* Position at center of segment */
                ribs[0].style.top = `${segmentSize / 2 - ribLength / 2 - 10}px`; /* Adjusted top for vertical alignment */
                ribs[0].style.transform = `rotate(-80deg) translateX(-${ribLength / 2}px)`; /* Even more aggressive rotation for curve */
                ribs[0].style.transformOrigin = `0% 50%`; /* Pivot from the left edge */

                /* Rib 2 (right) */
                ribs[1].style.left = `${segmentSize / 2 - 2}px`; /* Position at center of segment */
                ribs[1].style.top = `${segmentSize / 2 - ribLength / 2 - 10}px`; /* Adjusted top for vertical alignment */
                ribs[1].style.transform = `rotate(80deg) translateX(${ribLength / 2}px)`; /* Even more aggressive rotation for curve */
                ribs[1].style.transformOrigin = `100% 50%`; /* Pivot from the right edge */
            }
        }
    });
}

// Initial rendering
updateSnakePosition();

// Simple movement for demonstration (will be replaced by real movement)
let headX = snake[0].x;
let headY = snake[0].y;
let headRotation = snake[0].rotation;

document.addEventListener('mousemove', (e) => {
    const mouseX = e.clientX;
    const mouseY = e.clientY;

    // Update head position and rotation
    const head = snake[0];
    const dx = mouseX - head.x;
    const dy = mouseY - head.y;
    const angle = Math.atan2(dy, dx);

    head.rotation = angle * 180 / Math.PI;

    // Smoothly move head towards mouse
    head.x += dx * 0.08; /* Increased speed for responsiveness */
    head.y += dy * 0.08;

    // Update body segments to follow the head, maintaining fixed distance
    for (let i = 1; i < snake.length; i++) {
        const prevSegment = snake[i - 1];
        const currentSegment = snake[i];

        const dx = prevSegment.x - currentSegment.x;
        const dy = prevSegment.y - currentSegment.y;
        const distance = Math.sqrt(dx * dx + dy * dy);

        if (distance > segmentSize) { /* Only adjust if segments are too far apart */
            const ratio = segmentSize / distance;
            currentSegment.x = prevSegment.x - (dx * ratio);
            currentSegment.y = prevSegment.y - (dy * ratio);
        }

        /* Update rotation based on the new positions */
        currentSegment.rotation = Math.atan2(prevSegment.y - currentSegment.y, prevSegment.x - currentSegment.x) * 180 / Math.PI + 180;
    }

    updateSnakePosition();
});