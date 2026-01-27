extern "C" {
#include "node_api.h"
#include "operator_api.h"
#include "operator_types.h"
}


#include <string.h>

#include <cassert>
#include <cmath>
#include <cstdint>
#include <iostream>
#include <memory>
#include <vector>
#include <unistd.h>

#include <stdio.h>

// int sumnum;

typedef struct
{
  double x;
  double y;
} Data;

typedef struct
{
    std::vector<double> x_ref;
    std::vector<double> y_ref;
} WayPoint;

int run(void * dora_context)
{
    while(true){
    usleep(10000);
    // sumnum++;
    // std::cout<<sumnum<<std::endl;
    void * event = dora_next_event(dora_context);

    if (event == NULL) {
        printf("[c node] ERROR: unexpected end of event\n");
        return -1;
    }

    enum DoraEventType ty = read_dora_event_type(event);

    if (ty == DoraEventType_Input) {
        FILE * file = fopen("Waypoints.txt", "r");
        if (file == NULL) {
            printf("Failed to open file\n");
            return -1;
        }
        // printf("------------------------");

        Data data;
        WayPoint waypoint;
        int count = 0;

        while (fscanf(file, "%lf %lf", &data.x, &data.y) == 2) 
        {
            double x = data.x;
            double y = data.y;
            waypoint.x_ref.push_back(x);
            waypoint.y_ref.push_back(y);
        }

        fclose(file);
        std::string out_id = "road_lane"; 
        std::vector<char> output_data; 
        for(const auto & x: waypoint.x_ref)
        { 
            double v=x; 
            char* temp = reinterpret_cast<char*>(&v); 
            output_data.insert(output_data.end(), temp, temp + sizeof(double)); 
        } 

        for(const auto & y: waypoint.y_ref)
        { 
            double v=y; 
            char* temp = reinterpret_cast<char*>(&v); 
            output_data.insert(output_data.end(), temp, temp + sizeof(double));  
        } 

        size_t output_data_len = output_data.size();
        int result = dora_send_output(dora_context, &out_id[0], out_id.size(), output_data.data(), output_data_len);
        if (result != 0)
        {
            std::cerr << "failed to send output" << std::endl;
        }
    } 
    
    else if (ty == DoraEventType_Stop) {
        printf("[c node] received stop event\n");
    } 
    else {
        printf("[c node] received unexpected event: %d\n", ty);
    }
    free_dora_event(event);
  }
  return 0;
}

int main()
{
    std::cout << "test gnss poser for dora " << std::endl;
    auto dora_context = init_dora_context_from_env();
    auto ret = run(dora_context);
    free_dora_context(dora_context);

    std::cout << "exit test gnss poser ..." << std::endl;
    return ret;
}
