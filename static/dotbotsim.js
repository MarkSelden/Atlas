var scaleFactor = 1;

function coordinates2pixels(x,y) {
    return (10*x,10*y)
}

function gettingThingsInPlace() {
    // arming click events on buttons
    $("#nextbutton").click(function(){
        $.post('next')
    });
    $("#playbutton").click(function(){
        $.post('play')
    });
    $("#pausebutton").click(function(){
        $.post('pause')
    });
}

function getFloorplan() {
    $.getJSON( "/floorplan.json", function( floorplan ) {
        drawFloorplan(floorplan);
    });
}

function drawFloorplan(floorplan) {
    var svg = d3.select("#floorplan");
    
    // determine scalefactor such that map fill entire width of screen
    scaleFactor = ($('body').innerWidth()-50) / floorplan.width;
    
    // scale map to fill up screen
    svg.attr("width",  scaleFactor*floorplan.width)
       .attr("height", scaleFactor*floorplan.height);
    
    // position walls
    svg.selectAll("rect")
        .data(floorplan.obstacles)
        .enter().append("rect")
            .attr("x",      function(d) { return scaleFactor*d.x; })
            .attr("y",      function(d) { return scaleFactor*d.y; })
            .attr("width",  function(d) { return scaleFactor*d.width; })
            .attr("height", function(d) { return scaleFactor*d.height; })
            .attr("class",  "obstacle");
    
    // position buttons and labels
    $("#nextbutton").offset(   { top: scaleFactor*floorplan.height+ 80 });
    $("#playbutton").offset(   { top: scaleFactor*floorplan.height+ 80 });
    $("#pausebutton").offset(  { top: scaleFactor*floorplan.height+ 80 });
    $("#timelabel").offset(    { top: scaleFactor*floorplan.height+ 80 });
    $("#versionlabel").offset( { top: scaleFactor*floorplan.height+140 });
}

function getDotBots() {
    $.getJSON( "/dotbots.json", function( data ) {
        drawDotBots(data);
    });
}

function drawDotBots(data) {
    var svg    = d3.select("#floorplan");
    
    // timelabel
    $("#timelabel").html(data.simulatedTime);
    
    // positionerror
    var positionerror  = svg.selectAll(".positionerror")
        .data(data.dotbots);
    positionerror
        .attr("x1", function(d) { return scaleFactor*d.x; })
        .attr("y1", function(d) { return scaleFactor*d.y; })
        .attr("x2", function(d) { return scaleFactor*d.orchestratorview_x; })
        .attr("y2", function(d) { return scaleFactor*d.orchestratorview_y; });
    positionerror
        .enter().append("line")
            .attr("x1", function(d) { return scaleFactor*d.x; })
            .attr("y1", function(d) { return scaleFactor*d.y; })
            .attr("x2", function(d) { return scaleFactor*d.orchestratorview_x; })
            .attr("y2", function(d) { return scaleFactor*d.orchestratorview_y; })
            .attr("class", "positionerror");
    
    // orchestratorview
    var orchestratorview = svg.selectAll(".orchestratorview")
        .data(data.dotbots);
    orchestratorview
        .transition()
            .attr("cx", function(d) { return scaleFactor*d.orchestratorview_x; })
            .attr("cy", function(d) { return scaleFactor*d.orchestratorview_y; });
    orchestratorview
        .enter().append("circle")
            .attr("cx", function(d) { return scaleFactor*d.orchestratorview_x; })
            .attr("cy", function(d) { return scaleFactor*d.orchestratorview_y; })
            .attr("class", "orchestratorview")
            .attr("r", 6);
    
    // collisionpath
    var collisionpaths  = svg.selectAll(".collisionpath")
        .data(data.dotbots);
    collisionpaths
        .attr("x1", function(d) { return scaleFactor*d.x; })
        .attr("y1", function(d) { return scaleFactor*d.y; })
        .attr("x2", function(d) { return d.next_bump_x === null ? scaleFactor*d.x : scaleFactor*d.next_bump_x; })
        .attr("y2", function(d) { return d.next_bump_y === null ? scaleFactor*d.y : scaleFactor*d.next_bump_y; });
    collisionpaths
        .enter().append("line")
            .attr("x1", function(d) { return scaleFactor*d.x; })
            .attr("y1", function(d) { return scaleFactor*d.y; })
            .attr("x2", function(d) { return d.next_bump_x === null ? scaleFactor*d.x : scaleFactor*d.next_bump_x; })
            .attr("y2", function(d) { return d.next_bump_y === null ? scaleFactor*d.y : scaleFactor*d.next_bump_y; })
            .attr("class", "collisionpath");
    
    // dotbots
    var dotbots = svg.selectAll(".dotbot")
        .data(data.dotbots);
    dotbots
        .transition()
            .attr("cx", function(d) { return scaleFactor*d.x; })
            .attr("cy", function(d) { return scaleFactor*d.y; });
    dotbots
        .enter().append("circle")
            .attr("cx", function(d) { return scaleFactor*d.x; })
            .attr("cy", function(d) { return scaleFactor*d.y; })
            .attr("class", "dotbot")
            .attr("r", 6);
    
    // discoveredobstacles
    var discoveredobstacles = svg.selectAll(".discoveredobstacle")
        .data(data.discoveredobstacles);
    discoveredobstacles
        .transition()
            .attr("cx", function(d) { return scaleFactor*d[0]; })
            .attr("cy", function(d) { return scaleFactor*d[1]; });
    discoveredobstacles
        .enter().append("circle")
            .attr("cx", function(d) { return scaleFactor*d[0]; })
            .attr("cy", function(d) { return scaleFactor*d[1]; })
            .attr("class", "discoveredobstacle")
            .attr("r", 2);
}
