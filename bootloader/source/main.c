#include "gpio.h"
#include "uart.h"

#define RPI_BOOT (0x8000)

extern void PUT32( unsigned int address, unsigned int value );
extern void BRANCHTO( unsigned int );

void load_program();

int boot_main()
{
    init_uart();
    put_string("Bootloader waiting (press \"g\" once you've loaded your program)\r\n");
    load_program();
    return 0;
}

/// Load a program in ihex format from UART. Once it's loaded, execute it.
void load_program()
{
    // We have to parse the ihex format and for that we'll use a state machine.
    // This is based on the bootloader by David Welch (https://github.com/dwelch67/raspberrypi/blob/master/bootloader07/bootloader07.c)
    // the Intel HEX format is described at (https://en.wikipedia.org/wiki/Intel_HEX)
    // 
    // The ihex format breaks data into lines, each line starting with a :
    // The state machine reads each line and resets to state 1 when it sees a :
    //
    // States:
    //   [0]        nothing
    //   [1 - 2]    parse data byte count (2 digits)
    //   [3 - 6]    parse address offset (4 digits, big endian)
    //   [7]        parse record type (2 digits)
    //   [8]        parse record type (2nd digit) and then change state based on record type
    //   [9 - 12]   parse Exended Segment Address (ESA) record
    //   [13]       multiply ESA by 4 as per specifications and wait for the next line
    //   [14 - 21]  parse the data field, if state == 21, store data into RAM at the correct address   
    //
    // State Transitions:
    //   * > 1      when start code is received (ra == ':')
    //   * > 0      when a newline (\r or \n) is received
    //   * > 0      'g' or 'G' is received, also branches to main code
    //   1 ... 8    increment state as each char is parsed
    //   8 > 14     data record
    //   8 > 9      ESA record
    //   8 > 0      End of File record (also prints a hex string for some reason)
    //   8 > 0      Any record other than 0, 1 2
    //   9 ... 13   increment as each char is parsed
    //   13 > 0     always
    //   14 .. 21   increment as each char is parsed
    //   21 > 14    always (to parse more data)
    //
    // Cool tricks:
    //   - The following code:  if (ra > 0x39) ra -= 7; <variable> |= (ra & 0x0F);
    //     Looks weird but consider that hex value of '0' is 0x30 and '9' = 0x39, and 'A' = 0x41.
    //     Thus 'A' - 7 = 0x3A and 'F' - 7 = 0x3F. Then, & 0x0F to get the actual value!
    //     

    unsigned int state;
    unsigned int byte_count;
    unsigned int address;
    unsigned int record_type;
    unsigned int segment;
    unsigned int data;
    unsigned int sum;
    unsigned int ra;

    state=0;
    segment=0;
    sum=0;
    data=0;
    record_type=0;
    address=0;
    byte_count=0;
    while(1)
    {
        ra = get_char();
        if(ra==':')
        {
            state=1;
            continue;
        }
        if((ra == '\r') || (ra == '\n'))
        {
            state=0;
            continue;
        }
        if((ra=='g')||(ra=='G'))
        {
            put_string("\r--\r\n\n");
            BRANCHTO(RPI_BOOT);
            state=0;
            break;
        }
        switch(state)
        {
            case 0:
            {
                break;
            }
            case 1:
            case 2:
            {
                byte_count<<=4;
                if(ra>0x39) ra-=7;
                byte_count|=(ra&0xF);
                byte_count&=0xFF;
                state++;
                break;
            }
            case 3:
            case 4:
            case 5:
            case 6:
            {
                address<<=4;
                if(ra>0x39) ra-=7;
                address|=(ra&0xF);
                address&=0xFFFF;
                address|=segment;
                state++;
                break;
            }
            case 7:
            {
                record_type<<=4;
                if(ra>0x39) ra-=7;
                record_type|=(ra&0xF);
                record_type&=0xFF;
                state++;
                break;
            }
            case 8:
            {
                record_type<<=4;
                if(ra>0x39) ra-=7;
                record_type|=(ra&0xF);
                record_type&=0xFF;
                switch(record_type)
                {
                    case 0x00:
                    {
                        state=14;
                        break;
                    }
                    case 0x01:
                    {
                        print_hex(sum);
                        state=0;
                        break;
                    }
                    case 0x02:
                    {
                        state=9;
                        break;
                    }
                    default:
                    {
                        state=0;
                        break;
                    }
                }
                break;
            }
            case 9:
            case 10:
            case 11:
            case 12:
            {
                segment<<=4;
                if(ra>0x39) ra-=7;
                segment|=(ra&0xF);
                segment&=0xFFFF;
                state++;
                break;
            }
            case 13:
            {
                segment<<=4;
                state=0;
                break;
            }
            case 14:
            case 15:
            case 16:
            case 17:
            case 18:
            case 19:
            case 20:
            case 21:
            {
                data<<=4;
                if(ra>0x39) ra-=7;
                data|=(ra&0xF);
                if(state==21)
                {
                    ra=(data>>24)|(data<<24);
                    ra|=(data>>8)&0x0000FF00;
                    ra|=(data<<8)&0x00FF0000;
                    data=ra;
                    PUT32(address,data);
                    sum+=address;
                    sum+=data;
                    address+=4;
                    state=14;
                }
                else
                {
                    state++;
                }
                break;
            }
        }
    }
}
//-------------------------------------------------------------------------
//-------------------------------------------------------------------------


//-------------------------------------------------------------------------
//
// Copyright (c) 2014 David Welch dwelch@dwelch.com
//
// Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
//
// The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
//
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
//
//-------------------------------------------------------------------------
