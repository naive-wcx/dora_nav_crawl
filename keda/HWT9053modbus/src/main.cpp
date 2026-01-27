extern "C"
{
#include "node_api.h"
#include "operator_api.h"
#include "operator_types.h"
}
#include <stdio.h>
#include <time.h>
#include <sys/time.h>
#include "serial.h"
#include "wit_c_sdk.h"
#include "REG.h"
#include <stdint.h>
//#include <wiringSerial.h>
#include <unistd.h>
#include "imu_msg.h"
#include <string>
#include <iostream>
#include <iomanip> 
#include <cmath>

#define ACC_UPDATE		0x01
#define GYRO_UPDATE		0x02
#define ANGLE_UPDATE	0x04
#define MAG_UPDATE		0x08
#define TEMP_UPDATE     0x10
#define READ_UPDATE		0x80

static int fd, s_iCurBaud = 230400;
static volatile char s_cDataUpdate = 0 , s_cCmd = 0xff ;

const int c_uiBaud[] = {2400 , 4800 , 9600 , 19200 , 38400 , 57600 , 115200 , 230400 , 460800 , 921600};

static void AutoScanSensor(char* dev);
static void CopeSensorData(uint32_t uiReg, uint32_t uiRegNum);
static void SensorUartSend(uint8_t *p_data , uint32_t uiSize);
static void Delayms(uint16_t ucMs);

int main(int argc,char* argv[])
{
	std::cout << "pub imu node " << std::endl;
    auto dora_context = init_dora_context_from_env();
	// std::cout << "***************************" << std::endl;
	char* dev_ptr = "/dev/ttyUSB0";
	unsigned char* unsigned_cdev_ptr = reinterpret_cast<unsigned char*>(dev_ptr);

    if((fd = serial_open(unsigned_cdev_ptr, s_iCurBaud)<0))
	{
		printf("open %s fail\n", unsigned_cdev_ptr);
		return 0;
	}
	else printf("open %s success\n", unsigned_cdev_ptr);

	float fAcc[3], fGyro[3], fAngle[3],fTemp;
	int i , ret , iBuff;
	unsigned char cBuff[1];
	
	WitInit(WIT_PROTOCOL_905x_MODBUS, 0xff);

	WitRegisterCallBack(CopeSensorData);


	WitSerialWriteRegister(SensorUartSend);
	printf("\r\n********************** wit-motion HWT905xModbus example  ************************\r\n");
	AutoScanSensor(dev_ptr);
	while(1)
	{	
		void * event = dora_next_event(dora_context);

		if (event == NULL) {
			printf("[c node] ERROR: unexpected end of event\n");
			return -1;
		}

		enum DoraEventType ty = read_dora_event_type(event);

		if (ty == DoraEventType_Input) 
		{
			WitReadReg(AX,16);
			// Delayms(500);    
			
			while(serial_read_data(fd, cBuff, 1))
			{
				WitSerialDataIn(cBuff[0]);
			}
			struct imu_msg_h imu;
			if(s_cDataUpdate)
			{
				for(i = 0; i < 3; i++)
				{
					fAcc[i] = sReg[AX+i] / 32768.0f * 16.0f;
					fGyro[i] = sReg[GX+i] / 32768.0f * 2000.0f;
					iBuff =(((uint32_t)sReg[HRoll + 2*i]) << 16) | ((uint16_t)sReg[LRoll + 2*i]);
					fAngle[i] = (float)iBuff / 1000.0f;
				}
				fTemp = (float)sReg[TEMP905x]/100.0f;
				// printf("\n");

				static int num = 0;
				num++;

				struct timeval tv;
				gettimeofday(&tv, NULL);//获取时间
				
				if(s_cDataUpdate & ACC_UPDATE)
				{
					//X、Y 和 Z 轴的加速度值
					// printf("acc:%.3f %.3f %.3f\r\n", fAcc[0], fAcc[1], fAcc[2]);
					imu.linear_acceleration.x = fAcc[0] * 9.80665;
					imu.linear_acceleration.y = fAcc[1] * 9.80665;
					imu.linear_acceleration.z = fAcc[2] * 9.80665;
					s_cDataUpdate &= ~ACC_UPDATE;
				}
				if(s_cDataUpdate & GYRO_UPDATE)
				{
					//X、Y 和 Z 轴的角速度值
					// printf("gyro:%.4f %.4f %.4f\r\n", fGyro[0], fGyro[1], fGyro[2]);
					imu.angular_velocity.x = fGyro[0] * M_PI/180;  //rad/s
					imu.angular_velocity.y = fGyro[1] * M_PI/180;
					imu.angular_velocity.z = fGyro[2] * M_PI/180;
					// imu.angular_velocity.x = fGyro[0];
					// imu.angular_velocity.y = fGyro[1];
					// imu.angular_velocity.z = fGyro[2];
					s_cDataUpdate &= ~GYRO_UPDATE;
				}
				imu.stamp = tv.tv_sec + tv.tv_usec * 1e-6;
				// std::cout << std::fixed << std::setprecision(6)<< "time stamp: " << imu.stamp << " num: " << num << std::endl;
				// if(s_cDataUpdate & ANGLE_UPDATE)
				// {
				// 	printf("angle:%.3f %.3f %.3f\r\n", fAngle[0], fAngle[1], fAngle[2]);
				// 	s_cDataUpdate &= ~ANGLE_UPDATE;
				// }
				// if(s_cDataUpdate & MAG_UPDATE)
				// {
				// 	printf("mag:%d %d %d\r\n", sReg[HX], sReg[HY], sReg[HZ]);
				// 	s_cDataUpdate &= ~MAG_UPDATE;
				// }
				// if(s_cDataUpdate & TEMP_UPDATE)
				// {
				// 	printf("temp:%.1f\r\n", fTemp);
				// 	s_cDataUpdate &= ~TEMP_UPDATE;
				// }
				std::string out_id = "imu_msg";
				struct imu_msg_h* imu_out = &imu;
    			char * output_data = (char*)imu_out;
				// std::cout << "output_data_len: " << output_data_len << std::endl;
				int result = dora_send_output(dora_context, &out_id[0], out_id.length(), output_data, sizeof(imu_msg_h));
				// struct timeval tv_1;
				// gettimeofday(&tv_1, NULL);//获取时间
				// std::cout << "pub time : " << tv_1.tv_sec + tv_1.tv_usec * 1e-6 << " num: " << num << std::endl;
				if (result != 0)
				{
					// std::cerr << "failed to send output" << std::endl;
					printf("failed to send output");
				}

				s_cDataUpdate = 0;
			}
		}	
		else if (ty == DoraEventType_Stop)
        {
            printf("[c node] received stop event\n");
        }
        else
        {
            printf("[c node] received unexpected event: %d\n", ty);
        }

		free_dora_event(event);
	}
    serial_close(fd);
	// std::cout << "close!" << std::endl;
	free_dora_context(dora_context);

	return 0;
}

static void CopeSensorData(uint32_t uiReg, uint32_t uiRegNum)
{
    int i;
    for(i = 0; i < uiRegNum; i++)
    {
        switch(uiReg)
        {
            case AZ:
				s_cDataUpdate |= ACC_UPDATE;
            break;
            case GZ:
				s_cDataUpdate |= GYRO_UPDATE;
            break;
            case HZ:
				s_cDataUpdate |= MAG_UPDATE;
            break;
            case Yaw:
				s_cDataUpdate |= ANGLE_UPDATE;
            break;
			case TEMP905x:
				s_cDataUpdate |= TEMP_UPDATE;
            break;
            default:
				s_cDataUpdate |= READ_UPDATE;
			break;
        }
		uiReg++;
    }
}

static void Delayms(uint16_t ucMs)
{ 
     usleep(ucMs*1000);
}

static void SensorUartSend(uint8_t *p_data , uint32_t uiSize)
{
	uint32_t uiDelayUs = 0;
	
	uiDelayUs = ( (1000000/(s_iCurBaud/10)) *  uiSize  )   +  300 ;
	
	serial_write_data(fd,p_data,uiSize);
	
	usleep(uiDelayUs);
}

static void AutoScanSensor(char* dev)
{
	int i, iRetry;
	unsigned char cBuff[1];
	unsigned char* unsigned_cdev = reinterpret_cast<unsigned char*>(dev);
	// for(i = 7; i < sizeof(c_uiBaud)/sizeof(c_uiBaud[0]); i++)
	// {
		
	serial_close(fd);
	s_iCurBaud = c_uiBaud[7];
	fd = serial_open(unsigned_cdev , c_uiBaud[7]);
	iRetry = 2;
	s_cDataUpdate = 0;
	do
	{
		
		WitReadReg(AX, 3);
		Delayms(20);
		while(serial_read_data(fd, cBuff, 1))
		{
			WitSerialDataIn(cBuff[0]);
		}
		
		if(s_cDataUpdate != 0)
		{
			printf("%d baud find sensor\r\n\r\n", c_uiBaud[7]);
			return ;
		}
		iRetry--;
	}while(iRetry);		
	// }
	printf("can not find sensor\r\n");
	printf("please check your connection\r\n");
}
