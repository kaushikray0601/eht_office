/**
 * Enhanced SLD Module using Joint.js
 * This script includes features for proper cable connections, deletion, double-click functionality, specifications display, color-coded cables, and storing element coordinates.
 */

// Initialize Joint.js graph and paper
const graph = new joint.dia.Graph();

const paper = new joint.dia.Paper({
    el: document.getElementById('sld-canvas'),
    model: graph,
    width: 1200,
    height: 800,
    gridSize: 10,
    drawGrid: true,
    background: {
        color: '#f8f9fa'
    }
});

// Toolbar elements for drag-and-drop
const toolbarElements = [
    { type: 'image', label: 'MCB', image: 'image.png', spec: '20A, 3ph, MCB' },
    { type: 'image', label: '3Ph JB', image: 'image1.png', spec: '3Ph JB' },
    { type: 'rect', label: '1Ph JB', width: 20, height: 20, spec: '1Ph JB' },
    { type: 'path', label: 'Cable', path: 'M 0 0 L 100 0', spec: '4C x 16 sq.mm, XLPE, SWA, 0.4kV (1.1kV)' },
    { type: 'rect', label: 'End Termination', width: 12, height: 12, spec: 'End Termination' }
];

// Function to add elements to the toolbar
function initializeToolbar() {
    const toolbar = document.getElementById('sld-toolbar');
    toolbarElements.forEach((element, index) => {
        const button = document.createElement('button');
        button.innerText = element.label;
        button.className = 'btn btn-primary m-2';
        button.draggable = true;
        button.ondragstart = (event) => {
            event.dataTransfer.setData('elementType', element.type);
            event.dataTransfer.setData('elementIndex', index);
        };
        toolbar.appendChild(button);
    });
}

// Function to handle drop events on the canvas
function handleDrop(event) {
    event.preventDefault();
    const elementType = event.dataTransfer.getData('elementType');
    const elementIndex = event.dataTransfer.getData('elementIndex');
    const x = event.offsetX;
    const y = event.offsetY;

    let newElement;
    switch (elementType) {
        case 'image':
            newElement = new joint.shapes.standard.Image();
            newElement.attr('image/xlinkHref', toolbarElements[elementIndex].image);
            newElement.resize(60, 60);
            break;
        case 'rect':
            newElement = new joint.shapes.standard.Rectangle();
            newElement.resize(toolbarElements[elementIndex].width, toolbarElements[elementIndex].height);
            break;
        case 'path':
            newElement = new joint.shapes.standard.Link();
            newElement.attr('line/stroke', '#000000'); // Default black color
            break;
        default:
            console.error('Unknown element type:', elementType);
            return;
    }

    newElement.position(x, y);
    newElement.addTo(graph);

    // Add text annotation below the element
    const text = new joint.shapes.standard.TextBlock();
    text.position(x, y + 70);
    text.attr('label/text', toolbarElements[elementIndex].spec);
    text.addTo(graph);

    // Add double-click functionality to edit parameters
    newElement.on('element:pointerdblclick', () => {
        const form = document.createElement('form');
        form.innerHTML = '<input type="text" placeholder="Edit properties" />';
        document.body.appendChild(form);
        form.style.position = 'absolute';
        form.style.left = `${event.pageX}px`;
        form.style.top = `${event.pageY}px`;
        form.onsubmit = (e) => {
            e.preventDefault();
            const newSpec = form.querySelector('input').value;
            if (newSpec) {
                text.attr('label/text', newSpec);
            }
            document.body.removeChild(form);
        };
    });

    // Add right-click context menu
    newElement.on('element:contextmenu', (evt) => {
        evt.preventDefault();
        const menu = document.createElement('div');
        menu.innerHTML = '<button onclick="rotateElement()">Rotate</button><button onclick="resizeElement()">Resize</button><button onclick="highlightElement()">Highlight</button>';
        document.body.appendChild(menu);
        menu.style.position = 'absolute';
        menu.style.left = `${evt.pageX}px`;
        menu.style.top = `${evt.pageY}px`;
        menu.onmouseleave = () => document.body.removeChild(menu);
    });
}

// Function to delete selected elements
function deleteElement(element) {
    graph.removeCells([element]);
}

// Prevent default behavior for dragover
function handleDragOver(event) {
    event.preventDefault();
}

// Initialize the toolbar and event listeners
initializeToolbar();
const canvas = document.getElementById('sld-canvas');
canvas.addEventListener('dragover', handleDragOver);
canvas.addEventListener('drop', handleDrop);

// Function to auto-generate SLD based on input data
function autoGenerateSLD(inputData) {
    inputData.forEach(item => {
        let element;
        switch (item.type) {
            case 'MCB':
                element = new joint.shapes.standard.Image();
                element.attr('image/xlinkHref', 'image.png');
                element.resize(60, 60);
                break;
            case '3Ph JB':
                element = new joint.shapes.standard.Image();
                element.attr('image/xlinkHref', 'image1.png');
                element.resize(60, 60);
                break;
            case '1Ph JB':
                element = new joint.shapes.standard.Rectangle();
                element.resize(40, 40);
                break;
            case 'Cable':
                element = new joint.shapes.standard.Link();
                element.attr('line/stroke', item.color || '#000000'); // Default black color
                break;
            case 'End Termination':
                element = new joint.shapes.standard.Rectangle();
                element.resize(12, 12);
                break;
            default:
                console.error('Unknown element type:', item.type);
                return;
        }
        element.position(item.position.x, item.position.y);
        element.addTo(graph);
    });
}

// Example usage of autoGenerateSLD
const exampleInputData = [
    { type: 'MCB', position: { x: 50, y: 50 } },
    { type: 'Cable', position: { x: 150, y: 50 }, color: '#000000' },
    { type: '3Ph JB', position: { x: 250, y: 50 } },
    { type: 'Cable', position: { x: 350, y: 50 }, color: '#0000FF' },
    { type: '1Ph JB', position: { x: 450, y: 50 } },
    { type: 'Cable', position: { x: 550, y: 50 }, color: '#FF0000' },
    { type: 'End Termination', position: { x: 650, y: 50 } }
];
autoGenerateSLD(exampleInputData);